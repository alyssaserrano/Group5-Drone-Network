from entities.packet import Packet
from utils import config


class DSRRouteRequest(Packet):
    def __init__(self, src, dst, req_id, path, simulator, creation_time, channel_id):
        super().__init__(req_id, config.HELLO_PACKET_LENGTH, creation_time, simulator, channel_id)
        self.src = src
        self.dst = dst
        self.req_id = req_id
        self.path = list(path)
        self.transmission_mode = 1  # broadcast


class DSRRouteReply(Packet):
    def __init__(self, route, simulator, creation_time, channel_id):
        super().__init__(0, config.HELLO_PACKET_LENGTH, creation_time, simulator, channel_id)
        self.route = list(route)
        self.transmission_mode = 0  # unicast


class DSRRouteError(Packet):
    def __init__(self, broken_link, simulator, creation_time, channel_id):
        super().__init__(0, config.HELLO_PACKET_LENGTH, creation_time, simulator, channel_id)
        self.broken_link = broken_link
        self.transmission_mode = 1  # broadcast
