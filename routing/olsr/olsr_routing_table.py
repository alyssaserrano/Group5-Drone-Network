from collections import defaultdict
from simulator.log import logger

class OlsrRoutingTable:
    def __init__(self, env, my_drone):
        self.env = env
        self.my_drone = my_drone
        self.routing_table = defaultdict(list)
        self.neighbor_table = {}
        self.mpr_set = set()
        self.mpr_selector_set = set()
        self.entry_life_time = 2 * 1e6

    def update_hello(self, packet, cur_time):
        self.neighbor_table[packet.src_drone.identifier] = cur_time

    def update_tc(self, packet, cur_time):
        for node in packet.mpr_selector_list:
            self.routing_table[node] = [packet.src_drone.identifier, 1, cur_time]

    def purge(self):
        for key, last_time in list(self.neighbor_table.items()):
            if last_time + self.entry_life_time < self.env.now:
                del self.neighbor_table[key]

    def best_next_hop(self, dst_id):
        if dst_id in self.routing_table:
            return self.routing_table[dst_id][0]
        else:
            return self.my_drone.identifier
