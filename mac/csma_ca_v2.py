import simpy
import random
from simulator.log import logger
from phy.phy import Phy
from utils import config
from utils.util_function import check_channel_availability


class CsmaCaV2:
    """
    CSMA/CA v2:
      - Same public API as CsmaCa: __init__(drone), mac_send(pkd), wait_ack(pkd),
        wait_idle_channel(sender_drone, drones), listen(channel_states, drones, pkd)
      - Keeps beacon logic (periodic broadcast beacons)
      - Differences vs v1:
          * p-persistent slotting during backoff (tx with probability p_tx per idle slot)
          * Separate, gentler contention for beacons
    """

    def __init__(self, drone):
        self.my_drone = drone
        self.simulator = drone.simulator
        self.rng_mac = random.Random(self.my_drone.identifier + self.my_drone.simulator.seed + 105)  # different salt
        self.env = drone.env
        self.phy = Phy(self)
        self.channel_states = self.simulator.channel_states
        self.enable_ack = True

        # --- processes tracking (kept identical shape) ---
        self.wait_ack_process_dict = dict()
        self.wait_ack_process_finish = dict()
        self.wait_ack_process_count = 0
        self.wait_ack_process = None

        # # --- v2 knobs (read from config with safe defaults) ---
        # # p-persistent probability when channel is idle to actually decrement one slot
        # self.p_tx = getattr(config, "CSMA_P_PERSIST", 0.6)
        # # max retries copied from config
        # self.max_retry = getattr(config, "MAX_RETRANSMISSION_ATTEMPT", 7)

        # # beacon controls
        # self.beacon_enabled = getattr(config, "BEACON_ENABLED", True)
        # # interval in microseconds (match your time units)
        # self.beacon_interval_us = getattr(config, "BEACON_INTERVAL_US", 100_000)  # 100 ms
        # # on-air length (bits) for beacon, used to compute TX time (fallback small)
        # self.beacon_length_bits = getattr(config, "BEACON_PACKET_LENGTH", 600)    # 75 bytes default

        # try to start beacon loop (does not error if disabled)
        # if self.beacon_enabled:
        #     # slight random jitter to avoid global alignment
        #     jitter = self.rng_mac.randint(0, int(0.25 * self.beacon_interval_us))
        #     self.env.process(self._beacon_loop(jitter))

    # --------------------------
    # API: identical signatures
    # --------------------------
    def mac_send(self, pkd):
        """
        Control when drone can send packet (p-persistent CSMA/CA variant)
        :param pkd: the packet that needs to send
        :return: none
        """
        transmission_attempt = pkd.number_retransmission_attempt[self.my_drone.identifier]

        # BEB (like v1), but we'll decrement per-slot with p-persistent gating
        contention_window = (config.CW_MIN + 1) * (2 ** (max(1, transmission_attempt) - 1)) - 1

        # Backoff chosen in slots; convert to time as we count down
        bo_slots = self.rng_mac.randint(0, max(0, contention_window - 1))
        to_wait = config.DIFS_DURATION  # we'll handle backoff as per-slot countdown

        logger.info('At time: %s (us) ---- UAV: %s sets its back-off slots: %s',
                    self.env.now, self.my_drone.identifier, bo_slots)

        while True:
            # 1) Wait until channel becomes idle
            yield self.env.process(self.wait_idle_channel(self.my_drone, self.simulator.drones))

            if pkd.number_retransmission_attempt[self.my_drone.identifier] == 1:
                pkd.first_attempt_time = self.env.now

            # 2) Start listen process (unchanged API/behavior)
            self.env.process(self.listen(self.channel_states, self.simulator.drones, pkd))

            # 3) First wait DIFS
            logger.info('At time: %s (us) ---- UAV: %s DIFS wait: %s us',
                        self.env.now, self.my_drone.identifier, to_wait)
            start_time = self.env.now
            try:
                yield self.env.timeout(to_wait)
                # 4) Then perform p-persistent per-slot countdown of backoff
                while bo_slots > 0:
                    # if channel becomes busy, listen() will interrupt us; otherwise we gate the countdown by p_tx
                    # p-persistent: only decrement a slot with probability p_tx
                    if self.rng_mac.random() < self.p_tx:
                        bo_slots -= 1
                    yield self.env.timeout(config.SLOT_DURATION)

                # if we got here without interrupt, we send
                key = ''.join(['mac_send', str(self.my_drone.identifier), '_', str(pkd.packet_id)])
                self.my_drone.mac_process_finish[key] = 1  # mark finished

                # Occupy channel to send
                with self.channel_states[self.my_drone.identifier].request() as req:
                    yield req

                    logger.info('At time: %s (us) ---- UAV: %s (v2) sending pkd id: %s',
                                self.env.now, self.my_drone.identifier, pkd.packet_id)

                    pkd.transmitting_start_time = self.env.now
                    transmission_mode = pkd.transmission_mode

                    tx_time_us = pkd.packet_length / config.BIT_RATE * 1e6  # transmission delay in us

                    if transmission_mode == 0:  # unicast
                        next_hop_id = pkd.next_hop_id
                        pkd.increase_ttl()

                        # PHY first (same order)
                        self.phy.unicast(pkd, next_hop_id)
                        yield self.env.timeout(tx_time_us)

                        if self.enable_ack:
                            logger.info('At time: %s (us) ---- UAV: %s waits ACK for pkd: %s',
                                        self.env.now, self.my_drone.identifier, pkd.packet_id)

                            key2 = ''.join(['wait_ack', str(self.my_drone.identifier), '_', str(pkd.packet_id)])
                            self.wait_ack_process = self.env.process(self.wait_ack(pkd))
                            self.wait_ack_process_dict[key2] = self.wait_ack_process
                            self.wait_ack_process_finish[key2] = 0

                            # keep the channel during SIFS + ACK to avoid collisions on ACK
                            ack_air_time = config.ACK_PACKET_LENGTH / config.BIT_RATE * 1e6
                            yield self.env.timeout(config.SIFS_DURATION + ack_air_time)

                    elif transmission_mode == 1:  # broadcast
                        pkd.increase_ttl()
                        self.phy.broadcast(pkd)
                        yield self.env.timeout(tx_time_us)

                    # successful send or broadcast exits the loop
                    break

            except simpy.Interrupt:
                # interrupted due to channel becoming busy
                already_wait = self.env.now - start_time
                logger.info('At time: %s (us) ---- UAV: %s back-off interrupted; waited=%s us',
                            self.env.now, self.my_drone.identifier, already_wait)

                to_wait = config.DIFS_DURATION
                # loop to retry

    def wait_ack(self, pkd):
        """
        Same semantics as v1; on timeout, penalize & requeue or drop.
        """
        try:
            yield self.env.timeout(config.ACK_TIMEOUT)
            self.my_drone.routing_protocol.penalize(pkd)

            logger.info('At time: %s (us) ---- (v2) ACK timeout for pkd: %s',
                        self.env.now, pkd.packet_id)

            if pkd.number_retransmission_attempt[self.my_drone.identifier] < self.max_retry:
                yield self.env.process(self.my_drone.packet_coming(pkd))
            else:
                self.simulator.metrics.mac_delay.append(
                    (self.simulator.env.now - pkd.first_attempt_time) / 1e3
                )

                key2 = ''.join(['wait_ack', str(self.my_drone.identifier), '_', str(pkd.packet_id)])
                self.my_drone.mac_protocol.wait_ack_process_finish[key2] = 1

                logger.info('At time: %s (us) ---- (v2) Drop pkd: %s',
                            self.env.now, pkd.packet_id)

        except simpy.Interrupt:
            # receive ACK in time
            logger.info('At time: %s (us) ---- (v2) UAV: %s received ACK for pkd: %s',
                        self.env.now, self.my_drone.identifier, pkd.packet_id)

    def wait_idle_channel(self, sender_drone, drones):
        """
        Identical signature/behavior as v1
        """
        while not check_channel_availability(self.channel_states, sender_drone, drones):
            yield self.env.timeout(config.SLOT_DURATION)

    def listen(self, channel_states, drones, pkd):
        """
        Identical signature/contract as v1. Triggers interrupt if the channel turns busy.
        """
        logger.info('At time: %s (us) ---- (v2) UAV: %s starts listening/back-off',
                    self.env.now, self.my_drone.identifier)

        key = ''.join(['mac_send', str(self.my_drone.identifier), '_', str(pkd.packet_id)])

        while self.my_drone.mac_process_finish[key] == 0:
            if not check_channel_availability(channel_states, self.my_drone, drones):
                if not self.my_drone.mac_process_dict[key].triggered:
                    self.my_drone.mac_process_dict[key].interrupt()
                    break
            yield self.env.timeout(1)
