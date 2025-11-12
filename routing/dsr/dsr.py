import random
from simulator.log import logger
from utils import config
from entities.packet import DataPacket
from routing.dsr.dsr_packet import DSRRouteRequest, DSRRouteReply, DSRRouteError
from routing.dsr.dsr_cache import DSRCache


class DSRProtocol:
    """Simplified Dynamic Source Routing implementation for the UAV network."""

    def __init__(self, simulator, drone):
        self.sim = simulator
        self.env = simulator.env
        self.node = drone
        self.cache = DSRCache()
        self.requests_seen = set()
        self.req_counter = 0

    # OUTGOING DATA

    def next_hop_selection(self, pkt):
        """Return next hop if known; otherwise initiate route discovery."""
        dest = pkt.dst_drone.identifier
        known_path = self.cache.lookup(dest)

        if known_path and self.node.identifier in known_path:
            nxt = self._next_in_path(known_path)
            if nxt:
                pkt.next_hop_id = nxt
                return True, pkt, False

        # If no route found → broadcast a Route Request
        self._initiate_discovery(dest)
        return False, None, True

    def _initiate_discovery(self, dest):
        """Broadcast a new Route Request (RREQ) for unknown destinations."""
        self.req_counter += 1
        rid = (self.node.identifier, self.req_counter)
        self.requests_seen.add(rid)

        config.GL_ID_HELLO_PACKET += 1
        ch = self.node.channel_assigner.channel_assign()
        rreq = DSRRouteRequest(
            src=self.node.identifier,
            dst=dest,
            req_id=rid,
            path=[self.node.identifier],
            simulator=self.sim,
            creation_time=self.env.now,
            channel_id=ch
        )
        self.node.transmitting_queue.put(rreq)
        logger.info("t=%s μs | %s broadcasted RREQ→%s", self.env.now, self.node.identifier, dest)

    
    def handle_packet(self, pkt, src):
        now, me = self.env.now, self.node.identifier

        # --- Route Request (RREQ) ---
        if isinstance(pkt, DSRRouteRequest):
            if pkt.req_id in self.requests_seen:
                return
            self.requests_seen.add(pkt.req_id)
            pkt.path.append(me)
            logger.info("t=%s μs | %s got RREQ from %s (path=%s)", now, me, src, pkt.path)

            if pkt.dst == me:
                self._send_reply(pkt)
            else:
                self._rebroadcast(pkt, exclude=src)

        # --- Route Reply (RREP) ---
        elif isinstance(pkt, DSRRouteReply):
            route = pkt.route
            if route:
                dest = route[-1]
                self.cache.learn(dest, route)
                logger.info("t=%s μs | %s learned route to %s: %s", now, me, dest, route)
            self._forward_reply(pkt)

        # --- Route Error (RERR) ---
        elif isinstance(pkt, DSRRouteError):
            bad = pkt.broken_link
            self.cache.forget(bad)
            logger.info("t=%s μs | %s cleared route through broken link %s", now, me, bad)

        # --- Data Packet ---
        elif isinstance(pkt, DataPacket):
            if pkt.dst_drone.identifier == me:
                logger.info("t=%s μs | %s received DATA id=%s", now, me, pkt.packet_id)
                self.sim.metrics.calculate_metrics(pkt)
            else:
                self._forward_data(pkt)

    def _send_reply(self, rreq):
        """Send RREP back to the RREQ origin along the reverse path."""
        config.GL_ID_HELLO_PACKET += 1
        ch = self.node.channel_assigner.channel_assign()
        route = list(rreq.path)
        reply = DSRRouteReply(route, self.sim, self.env.now, ch)
        reply.next_hop_id = route[-2]
        self.node.transmitting_queue.put(reply)
        logger.info("t=%s μs | %s replied with RREP along %s", self.env.now, self.node.identifier, route)

    def _rebroadcast(self, pkt, exclude):
        """Forward RREQ to all neighbors except the one it came from."""
        for n in self.node.neighbors:
            if n.identifier != exclude:
                jitter = random.uniform(0.0, 0.04)
                self.env.process(self._delayed_send(n, pkt, jitter))

    def _forward_reply(self, pkt):
        """Forward RREP toward the origin (reverse path)."""
        me = self.node.identifier
        if me in pkt.route:
            idx = pkt.route.index(me)
            if idx > 0:
                pkt.next_hop_id = pkt.route[idx - 1]
                self.node.transmitting_queue.put(pkt)

    def _forward_data(self, pkt):
        """Forward data packet along cached source route."""
        me = self.node.identifier
        route = self.cache.lookup(pkt.dst_drone.identifier)
        if route and me in route:
            nxt = self._next_in_path(route)
            if nxt:
                pkt.next_hop_id = nxt
                self.node.transmitting_queue.put(pkt)
                logger.info("t=%s μs | %s forwarded DATA→%s via %s",
                            self.env.now, me, pkt.dst_drone.identifier, nxt)

    def _next_in_path(self, path):
        """Find the next hop in the stored route list."""
        me = self.node.identifier
        if me in path:
            i = path.index(me)
            if i + 1 < len(path):
                return path[i + 1]
        return None

    def _delayed_send(self, neighbor, pkt, delay):
        yield self.env.timeout(delay)
        self.node.transmitting_queue.put(pkt)
