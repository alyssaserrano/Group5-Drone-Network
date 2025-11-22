import random
from simulator.log import logger
from entities.packet import DataPacket, AckPacket
from topology.virtual_force.vf_packet import VfPacket
from routing.olsr.olsr_packet import OlsrHelloPacket, OlsrTcPacket
from routing.olsr.olsr_routing_table import OlsrRoutingTable
from utils import config

class Olsr:
    def __init__(self, simulator, my_drone):
        self.simulator = simulator
        self.my_drone = my_drone
        self.rng_routing = random.Random(my_drone.identifier + simulator.seed + 10)
        self.table = OlsrRoutingTable(simulator.env, my_drone)
        self.hello_interval = 0.4 * 1e6
        self.tc_interval = 0.8 * 1e6
        self.simulator.env.process(self.broadcast_hello_periodically())
        self.simulator.env.process(self.broadcast_tc_periodically())
        self.simulator.env.process(self._purge_routes())

    def broadcast_hello(self):
        config.GL_ID_HELLO_PACKET += 1
        channel_id = self.my_drone.channel_assigner.channel_assign()
        hello_pkd = OlsrHelloPacket(
            src_drone=self.my_drone,
            creation_time=self.simulator.env.now,
            id_hello_packet=config.GL_ID_HELLO_PACKET,
            hello_packet_length=config.HELLO_PACKET_LENGTH,
            neighbors=list(self.table.neighbor_table.keys()),
            simulator=self.simulator,
            channel_id=channel_id
        )
        hello_pkd.transmission_mode = 1
        self.my_drone.transmitting_queue.put(hello_pkd)
        self.simulator.metrics.control_packet_num += 1
        logger.info("UAV %s broadcasted HELLO packet.", self.my_drone.identifier)

    def broadcast_hello_periodically(self):
        while True:
            self.broadcast_hello()
            yield self.simulator.env.timeout(self.hello_interval)

    def broadcast_tc(self):
        config.GL_ID_TC_PACKET += 1
        channel_id = self.my_drone.channel_assigner.channel_assign()
        tc_pkd = OlsrTcPacket(
            src_drone=self.my_drone,
            creation_time=self.simulator.env.now,
            id_tc_packet=config.GL_ID_TC_PACKET,
            tc_packet_length=config.HELLO_PACKET_LENGTH,
            mpr_selector_list=list(self.table.mpr_selector_set),
            simulator=self.simulator,
            channel_id=channel_id,
            seq_no=self.table.seq_no,
            hop_count=0
        )
        self.table.seq_no += 1

        tc_pkd.transmission_mode = 1
        self.my_drone.transmitting_queue.put(tc_pkd)
        self.simulator.metrics.control_packet_num += 1
        logger.info("UAV %s broadcasted TC packet.", self.my_drone.identifier)

    def broadcast_tc_periodically(self):
        while True:
            self.broadcast_tc()
            yield self.simulator.env.timeout(self.tc_interval)

    def next_hop_selection(self, packet):
        dst_drone = packet.dst_drone
        best_next_hop_id = self.table.best_next_hop(dst_drone.identifier)
        has_route = best_next_hop_id != self.my_drone.identifier
        packet.next_hop_id = best_next_hop_id
        return has_route, packet, False

    def packet_reception(self, packet, src_drone_id):
        """
        Handle incoming packets at the network layer (HELLO, TC, DATA).
        Expanded to behave more like AODV: dynamic route updates, buffering, and forwarding.
        """
        current_time = self.simulator.env.now

        # ---------------------------------------------------------------
        # 1. HELLO PACKET HANDLING
        # ---------------------------------------------------------------
        if isinstance(packet, OlsrHelloPacket):
            self.table.update_hello(packet, current_time)
            logger.info(
                "At time: %s (us) ---- UAV: %s received HELLO from neighbor %s.",
                current_time, self.my_drone.identifier, packet.src_drone.identifier
            )

        # ---------------------------------------------------------------
        # 2. TOPOLOGY CONTROL (TC) HANDLING
        # ---------------------------------------------------------------
        elif isinstance(packet, OlsrTcPacket):
            self.table.update_tc(packet, current_time)
            self.table.recompute_routes()
            logger.info(
                "At time: %s (us) ---- UAV: %s received TC from %s; routing table recomputed.",
                current_time, self.my_drone.identifier, packet.src_drone.identifier
            )

            # Try to resend any buffered packets if new routes became available
            for buffered_pkt in list(self.my_drone.waiting_list):
                has_route, pkt, _ = self.next_hop_selection(buffered_pkt)
                if has_route:
                    self.my_drone.transmitting_queue.put(pkt)
                    self.my_drone.waiting_list.remove(buffered_pkt)
                    logger.info(
                        "UAV %s resumed sending buffered packet %s after TC update.",
                        self.my_drone.identifier, buffered_pkt.packet_id
                    )

        # ---------------------------------------------------------------
        # 3. DATA PACKET HANDLING
        # ---------------------------------------------------------------
        elif isinstance(packet, DataPacket):
            dst_id = packet.dst_drone.identifier
            me = self.my_drone.identifier

            # (a) If I'm the destination
            if dst_id == me:
                self.simulator.metrics.calculate_metrics(packet)
                logger.info(
                    "At time: %s (us) ---- UAV: %s received DATA (id: %s) as DESTINATION.",
                    current_time, me, packet.packet_id
                )

            # (b) Otherwise, I'm a forwarder
            else:
                has_route, pkt, _ = self.next_hop_selection(packet)

                if has_route:
                    # Forward the packet via the next hop
                    self.my_drone.transmitting_queue.put(pkt)
                    logger.info(
                        "At time: %s (us) ---- UAV: %s FORWARD DATA (id: %s) to %s via next hop %s.",
                        current_time, me, packet.packet_id, dst_id, pkt.next_hop_id
                    )

                else:
                    # No route → buffer the packet and trigger proactive update
                    if len(self.my_drone.waiting_list) < self.my_drone.max_queue_size:
                        self.my_drone.waiting_list.append(packet)
                        logger.info(
                            "At time: %s (us) ---- UAV: %s NO ROUTE to %s; buffered DATA (id: %s).",
                            current_time, me, dst_id, packet.packet_id
                        )
                        # Trigger HELLO/TC updates for faster route formation
                        self.broadcast_hello()
                        self.broadcast_tc()
                    else:
                        logger.info(
                            "At time: %s (us) ---- UAV: %s DROPPED DATA (id: %s); buffer full.",
                            current_time, me, packet.packet_id
                        )

        # ---------------------------------------------------------------
        # 4. OTHER PACKETS (like VF)
        # ---------------------------------------------------------------
        elif hasattr(packet, "type") and packet.type == "VF":
            self.my_drone.motion_controller.neighbor_table.add_neighbor(packet, current_time)

        # ---------------------------------------------------------------
        # 5. SimPy Compatibility
        # ---------------------------------------------------------------
        yield self.simulator.env.timeout(1)

    def penalize(self, packet):
        next_hop = getattr(packet, 'next_hop_id', None)
        if next_hop:
            self.table.invalidate_routes_through(next_hop)
            logger.info("At time: %s (us) ---- OLSR invalidated routes through failed next hop %s",
                        self.simulator.env.now, next_hop)

    def _purge_routes(self):
        while True:
            self.table.purge()
            yield self.simulator.env.timeout(self.tc_interval)




