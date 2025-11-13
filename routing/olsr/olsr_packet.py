from entities.packet import Packet

class OlsrHelloPacket(Packet):
    def __init__(self, src_drone, creation_time, id_hello_packet,
                 hello_packet_length, neighbors, simulator, channel_id):
        super().__init__(id_hello_packet, hello_packet_length, creation_time, simulator, channel_id)
        self.src_drone = src_drone
        self.neighbors = neighbors  # neighbor list to share
        self.type = 'HELLO'


class OlsrTcPacket(Packet):
    def __init__(self, src_drone, creation_time, id_tc_packet,
                 tc_packet_length, mpr_selector_list, simulator, channel_id,
                 seq_no=0, hop_count=0):
        super().__init__(id_tc_packet, tc_packet_length, creation_time, simulator, channel_id)
        self.src_drone = src_drone
        self.mpr_selector_list = mpr_selector_list
        self.seq_no = seq_no
        self.hop_count = hop_count
        self.type = 'TC'

