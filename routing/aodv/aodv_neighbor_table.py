import simpy
from utils import config


class RouteTable:
    """Simple per-destination route table used by AODV wrapper.

    Entry format: dest_id -> { 'next_hop': id, 'seq': seqno, 'hops': int, 'timer': Process }
    """

    def __init__(self, env, my_drone, route_lifetime=None):
        self.env = env
        self.my_drone = my_drone
        self.table = {}
        self.route_lifetime = route_lifetime if route_lifetime is not None else 300

    def _expire(self, dest):
        try:
            yield self.env.timeout(self.route_lifetime)
            if dest in self.table:
                del self.table[dest]
        except simpy.Interrupt:
            return

    def install_route(self, dest, next_hop, dest_seq=0, hop_count=0, refresh_only=False):
        old = self.table.get(dest)
        should_replace = False
        if old is None:
            should_replace = True
        else:
            old_seq = old.get('seq', 0)
            old_hops = old.get('hops', 0)
            if (dest_seq > old_seq) or (dest_seq == old_seq and hop_count < old_hops):
                should_replace = True

        if should_replace:
            if old is not None:
                # cancel old timer
                t = old.get('timer')
                if t is not None and not t.triggered:
                    t.interrupt('replace')
            timer = self.env.process(self._expire(dest))
            self.table[dest] = {'next_hop': next_hop, 'seq': dest_seq, 'hops': hop_count, 'timer': timer}
            return self.table[dest]

        # refresh lifetime if required
        if old is not None:
            t = old.get('timer')
            if t is not None and not t.triggered:
                t.interrupt('refresh')
            timer = self.env.process(self._expire(dest))
            old['timer'] = timer
            return old

        return None

    def get_route(self, dest):
        return self.table.get(dest)

    def invalidate_routes_through(self, next_hop):
        to_delete = [d for d,entry in self.table.items() if entry.get('next_hop') == next_hop]
        for d in to_delete:
            del self.table[d]

    def add_direct_neighbor(self, neighbor_id):
        # direct neighbor hop_count = 1, seq unknown (0)
        return self.install_route(neighbor_id, neighbor_id, dest_seq=0, hop_count=1)

    def purge(self):
        # table entries auto-expire by timers; this is a no-op kept for API compatibility
        return
