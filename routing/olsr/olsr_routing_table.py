from collections import defaultdict, deque
from simulator.log import logger

class OlsrRoutingTable:
    def __init__(self, env, my_drone):
        self.env = env
        self.my_drone = my_drone
        self.routing_table = defaultdict(list)
        self.neighbor_table = {}
        self.mpr_set = set()
        self.mpr_selector_set = set()
        self.entry_life_time = 8 * 1e6
        self.seq_no = 0

    def update_hello(self, packet, cur_time):
        self.neighbor_table[packet.src_drone.identifier] = cur_time
        self.recompute_routes()
        # Detect if MPR set or neighbors changed
        if packet.src_drone.identifier not in self.mpr_selector_set:
            self.mpr_selector_set.add(packet.src_drone.identifier)
            self.my_drone.routing_protocol.broadcast_tc()  # force immediate TC


    def update_tc(self, packet, cur_time):
        for node in packet.mpr_selector_list:
            dst_id = node
            next_hop_id = packet.src_drone.identifier
            hop_count = 1
            # Only update if this route is new or fresher
            if (dst_id not in self.routing_table or
                    cur_time > self.routing_table[dst_id][2]):
                self.routing_table[dst_id] = [next_hop_id, hop_count, cur_time]

    def purge(self):
        now = self.env.now
        for dst, (_, _, last_time) in list(self.routing_table.items()):
            if now - last_time > self.entry_life_time:
                del self.routing_table[dst]
                logger.info("Route to %s expired.", dst)
        for neighbor, last_time in list(self.neighbor_table.items()):
            if now - last_time > self.entry_life_time:
                del self.neighbor_table[neighbor]


    def best_next_hop(self, dst_id):
        if dst_id in self.routing_table:
            return self.routing_table[dst_id][0]
        else:
            return self.my_drone.identifier

    def invalidate_routes_through(self, next_hop):
        to_delete = [d for d, e in self.routing_table.items() if e[0] == next_hop]
        for d in to_delete:
            del self.routing_table[d]

    def recompute_routes(self):
        graph = defaultdict(set)
        # Build adjacency list from neighbor + TC info
        for node, last_seen in self.neighbor_table.items():
            graph[self.my_drone.identifier].add(node)
            graph[node].add(self.my_drone.identifier)
        for dst, (nh, _, _) in self.routing_table.items():
            graph[nh].add(dst)
            graph[dst].add(nh)

        # BFS to find shortest path (minimum hops)
        visited = {self.my_drone.identifier}
        queue = deque([(self.my_drone.identifier, None, 0)])
        new_routes = {}

        while queue:
            node, first_hop, hops = queue.popleft()
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_hop = first_hop if first_hop else neighbor
                    if neighbor not in new_routes or hops + 1 < new_routes[neighbor][1]:
                        new_routes[neighbor] = [next_hop, hops + 1, self.env.now]
                    queue.append((neighbor, next_hop, hops + 1))

        self.routing_table.update(new_routes)

