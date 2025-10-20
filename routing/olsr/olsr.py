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
        self.hello_interval = 0.5 * 1e6
        self.tc_interval = 1.0 * 1e6
        self.simulator.env.process(self.broadcast_hello_periodically())
        self.simulator.env.process(self.broadcast_tc_periodically())

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
            channel_id=channel_id
        )
        tc_pkd.transmission_mode = 1
        self.my_drone.transmitting_queue.put(tc_pkd)

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
        Packet reception at network layer
        """
        current_time = self.simulator.env.now

        if isinstance(packet, OlsrHelloPacket):
            self.table.update_hello(packet, current_time)

        elif isinstance(packet, OlsrTcPacket):
            self.table.update_tc(packet, current_time)

        elif isinstance(packet, DataPacket):
            # If it's a data packet for me
            if packet.dst_drone.identifier == self.my_drone.identifier:
                self.simulator.metrics.calculate_metrics(packet)
            else:
                has_route, pkt, _ = self.next_hop_selection(packet)
                if has_route:
                    self.my_drone.transmitting_queue.put(pkt)

        elif isinstance(packet, VfPacket):
            # Handle virtual force (motion control)
            self.my_drone.motion_controller.neighbor_table.add_neighbor(packet, current_time)

        # make sure it yields at least once so SimPy treats it as a generator
        yield self.simulator.env.timeout(1)

