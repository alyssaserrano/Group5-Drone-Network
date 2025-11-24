from entities.packet import Packet
from utils import config


class AodvHelloPacket(Packet):
    def __init__(self, src_drone, creation_time, id_hello_packet, hello_packet_length, simulator, channel_id):
        super().__init__(id_hello_packet, hello_packet_length, creation_time, simulator, channel_id)
        self.src_drone = src_drone


class RREQPacket(Packet):
    def __init__(self, origin, rreq_id, dst_id, dst_seq_req, hop_count, path, creation_time, packet_id, simulator, channel_id):
        # small control payload length (use HELLO size as baseline)
        super().__init__(packet_id, config.RREQ_PACKET_LENGTH, creation_time, simulator, channel_id)
        self.origin = origin
        self.rreq_id = rreq_id
        self.dst = dst_id
        self.dst_seq_req = dst_seq_req
        self.hop_count = hop_count
        self.path = list(path)
        self.transmission_mode = 1  # broadcast


class RREPPacket(Packet):
    def __init__(self, rep_src, origin, rep_dst_seq, rep_hops, rep_path, creation_time, packet_id, simulator, channel_id):
        super().__init__(packet_id, config.RREP_PACKET_LENGTH, creation_time, simulator, channel_id)
        self.rep_src = rep_src
        self.origin = origin
        self.rep_dst_seq = rep_dst_seq
        self.rep_hops = rep_hops
        self.rep_path = list(rep_path)
        self.transmission_mode = 0  # unicast by default when forwarded
        self.next_hop_id = None  # to be set when forwarding

class RERRPacket(Packet):
    """
    Minimal AODV Route Error.
    - 'sender' is the node detecting the break.
    - 'affected_dsts' is a list of destination IDs that became unreachable via the broken next hop.
    This is a simplified model: we broadcast once; receivers invalidate and optionally re-discover.
    """
    def __init__(self, sender, affected_dsts, creation_time, packet_id, simulator, channel_id):
        # keep control length small (reuse HELLO size)
        super().__init__(packet_id, config.RERR_PACKET_LENGTH, creation_time, simulator, channel_id)
        self.sender = sender
        self.affected_dsts = list(affected_dsts)
        self.transmission_mode = 1  # broadcast
