import logging
from utils import config
from .tech_profiles import wifi_11n  # Import tech_profiles.py file that has our wifi objects.
from .tech_profiles import wifi_11ac
from .tech_profiles import wifi_direct

# config logging
logging.basicConfig(filename='running_log.log',
                    filemode='w',  # there are two modes: 'a' and 'w'
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    level=config.LOGGING_LEVEL
                    )


class Phy:
    """
    Physical layer implementation

    Attributes:
        mac: mac protocol that installed
        env: simulation environment created by simpy
        my_drone: the drone that installed the physical protocol

    """

    def __init__(self, mac):
        self.mac = mac
        self.env = mac.env
        self.my_drone = mac.my_drone
        self.profile = wifi_11ac  # Our tech_profile object instantiation. 
        
        # Choose default power (TX)
        if self.profile.tx_power_levels:
            # Choose which TX power level to use
            self.current_tx_power_label = "high" if "medium" in self.profile.tx_power_levels else list(self.profile.tx_power_levels.keys())[0]
            self.current_tx_power_dbm = self.profile.tx_power_levels[self.current_tx_power_label]
        else:
            self.current_tx_power_label = "max"
            self.current_tx_power_dbm = self.profile.tx_power_range[1]
            
        # Debug for knowing if it is using our tech_profile.
        #print(f"[PHY INIT] drone {getattr(self.my_drone, 'identifier', '?')} assigned profile: {self.profile.name}, TX_mW={self.profile.energy_model.get('TX', 'N/A')}")
        
    def _consume_energy(self, mode, duration_s):
        power_mw = self.profile.energy_model.get(mode)
        if power_mw is None:
            return

        power_w = power_mw / 1000.0
        energy_j = power_w * duration_s
        # Not subtracting energy yet to avoid affecting sim
        self.my_drone.residual_energy -= energy_j

        # DEBUG
        # print(f"[POWER] mode={mode}, duration={duration_s:.6f}s, P={power_mw}mW, E={energy_j:.6e}J")
        
    # RX
    def rx_energy(self, packet):
        """
        Not connected yet
        will call this when a packet arrives.
        """
        # duration of receiving this packet
        rx_duration_s = packet.packet_length / config.BIT_RATE

        # FUTURE actual RX accounting:
        self._consume_energy("RX", rx_duration_s)

        # Debug
        # print(f"[POWER RX] drone {self.my_drone.identifier} would consume RX energy: {rx_duration_s:.6f}s")
        pass
    
    # idle
    def idle_energy(self, duration_s=1):
        # FUTURE actual Idle accounting:
        self._consume_energy("Idle", duration_s)

        # Debug 
        # print(f"[POWER IDLE] drone {self.my_drone.identifier} would consume Idle energy for {duration_s}s")
        pass


    def sleep(self, duration_s):
        # FUTURE actual Sleep accounting:
        self._consume_energy("Sleep", duration_s)

        # Debug 
        # print(f"[POWER SLEEP] drone {self.my_drone.identifier} would sleep for {duration_s}s")
        pass
    
    def unicast(self, packet, next_hop_id):
        """
        Unicast packet through the wireless channel

        Parameters:
            packet: the data packet or ACK packet that needs to be transmitted
            next_hop_id: the identifier of the next hop drone
        """

        # Debug
        #print(f"[PHY TX] drone {self.my_drone.identifier} unicast using profile '{self.profile.name}' | profile_TX_mW={self.profile.energy_model.get('TX','N/A')} | config_TX={config.TRANSMITTING_POWER}")

        # Calculate transmission duration
        tx_duration_s = packet.packet_length / config.BIT_RATE

        # Use power model to consume TX energy
        self._consume_energy("TX", tx_duration_s)

        # transmit through the channel
        message = [packet, self.env.now, self.my_drone.identifier, 0, packet.channel_id]

        self.my_drone.simulator.channel.unicast_put(message, next_hop_id)

    def broadcast(self, packet):
        """
        Broadcast packet through the wireless channel

        Parameters:
        packet: tha packet (hello packet, etc.) that needs to be broadcast
        """

        # Debug
        #print(f"[PHY TX] drone {self.my_drone.identifier} broadcast using profile '{self.profile.name}' | profile_TX_mW={self.profile.energy_model.get('TX','N/A')} | config_TX={config.TRANSMITTING_POWER}")

        tx_duration_s = packet.packet_length / config.BIT_RATE

        # Use power model to consume TX energy for sender
        self._consume_energy("TX", tx_duration_s)

        # For demonstration: simulate RX energy for sender (not typical, but shows usage)
        # self.rx_energy(packet)  # Uncomment if you want sender to also consume RX energy

        # energy consumption
        #energy_consumption = (packet.packet_length / config.BIT_RATE) * config.TRANSMITTING_POWER
        #self.my_drone.residual_energy -= energy_consumption

        # transmit through the channel
        message = [packet, self.env.now, self.my_drone.identifier, 0, packet.channel_id]

        self.my_drone.simulator.channel.broadcast_put(message)

    def multicast(self, packet, dst_id_list):
        """
        Multicast packet through the wireless channel

        Parameters:
            packet: tha packet that needs to be multicasted
            dst_id_list: list of ids for multicast destinations
        """

        # Debug
        #print(f"[PHY TX] drone {self.my_drone.identifier} multicast using profile '{self.profile.name}' | profile_TX_mW={self.profile.energy_model.get('TX','N/A')} | config_TX={config.TRANSMITTING_POWER}")

        # Calculate transmission duration
        tx_duration_s = packet.packet_length / config.BIT_RATE

        # Use power model to consume TX energy
        self._consume_energy("TX", tx_duration_s)
        # transmit through the channel
        message = [packet, self.env.now, self.my_drone.identifier, packet.channel_id]

        self.my_drone.simulator.channel.multicast_put(message, dst_id_list)
        


if __name__ == "__main__":
    print("------------STANDALONE POWER TEST------------")
    # Fake packet object for testing
    class FakeChannel:
        def broadcast_put(self, message):
            print("[FakeChannel] broadcast_put called with:", message)

    class FakeSimulator:
        channel = FakeChannel()

    class FakeDrone:
        identifier = "demo-drone"
        residual_energy = 100.0
        simulator = FakeSimulator()  # Add this line

    class FakeEnv:
        now = 0

    class FakeMAC:
        my_drone = FakeDrone()
        env = FakeEnv()
    class FakePacket:
        packet_length = 1000   # bits
        channel_id = 0
    # Instantiate PHY
    phy = Phy(FakeMAC())
    print("Profile loaded:", phy.profile.name)
    print("Current TX power level:", phy.current_tx_power_label, phy.current_tx_power_dbm, "dBm")
    print()
    print("Initial residual energy:", phy.my_drone.residual_energy)

    print("[TEST] Calling RX")
    phy.rx_energy(FakePacket())
    print("Residual energy after RX:", phy.my_drone.residual_energy)

    print("[TEST] Calling Idle")
    phy.idle_energy(duration_s=2)
    print("Residual energy after Idle:", phy.my_drone.residual_energy)

    print("[TEST] Calling Sleep")
    phy.sleep(duration_s=5)
    print("Residual energy after Sleep:", phy.my_drone.residual_energy)

    print("[TEST] Calling Broadcast")
    phy.broadcast(FakePacket())
    print("Residual energy after Broadcast:", phy.my_drone.residual_energy)

    print("\nTest complete.")


