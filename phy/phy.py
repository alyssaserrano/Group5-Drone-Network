import logging
from utils import config
from .tech_profiles import wifi_11n  # Import tech_profiles.py file that has our wifi objects.

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

    Author: Zihao Zhou, eezihaozhou@gmail.com
    Created at: 2024/1/11
    Updated at: 2025/3/30
    """

    def __init__(self, mac):
        self.mac = mac
        self.env = mac.env
        self.my_drone = mac.my_drone
        self.profile = wifi_11n  # Our tech_profile object instantiation. 

        # Debug for knowing if it is using our tech_profile.
        print(f"[PHY INIT] drone {getattr(self.my_drone, 'identifier', '?')} assigned profile: {self.profile.name}, TX_mW={self.profile.energy_model.get('TX', 'N/A')}")

    def unicast(self, packet, next_hop_id):
        """
        Unicast packet through the wireless channel

        Parameters:
            packet: the data packet or ACK packet that needs to be transmitted
            next_hop_id: the identifier of the next hop drone
        """

        # Debug
        print(f"[PHY TX] drone {self.my_drone.identifier} unicast using profile '{self.profile.name}' | profile_TX_mW={self.profile.energy_model.get('TX','N/A')} | config_TX={config.TRANSMITTING_POWER}")

        # energy consumption
        energy_consumption = (packet.packet_length / config.BIT_RATE) * config.TRANSMITTING_POWER
        self.my_drone.residual_energy -= energy_consumption

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
        print(f"[PHY TX] drone {self.my_drone.identifier} broadcast using profile '{self.profile.name}' | profile_TX_mW={self.profile.energy_model.get('TX','N/A')} | config_TX={config.TRANSMITTING_POWER}")

        # energy consumption
        energy_consumption = (packet.packet_length / config.BIT_RATE) * config.TRANSMITTING_POWER
        self.my_drone.residual_energy -= energy_consumption

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
        print(f"[PHY TX] drone {self.my_drone.identifier} multicast using profile '{self.profile.name}' | profile_TX_mW={self.profile.energy_model.get('TX','N/A')} | config_TX={config.TRANSMITTING_POWER}")

        # a transmission delay should be considered
        yield self.env.timeout(packet.packet_length / config.BIT_RATE * 1e6)

        # energy consumption
        energy_consumption = (packet.packet_length / config.BIT_RATE) * config.TRANSMITTING_POWER
        self.my_drone.residual_energy -= energy_consumption

        # transmit through the channel
        message = [packet, self.env.now, self.my_drone.identifier, packet.channel_id]

        self.my_drone.simulator.channel.multicast_put(message, dst_id_list)
