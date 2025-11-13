import random
import copy
from simulator.log import logger
from routing.aodv.aodv_packet import AodvHelloPacket, RREQPacket, RREPPacket
from routing.aodv.aodv_neighbor_table import RouteTable
from utils import config
from entities.packet import DataPacket


HELLO_INTERVAL = 10 * 1e6  # microseconds (match other modules unit)
REBROADCAST_JITTER = (0.0, 0.05)
ORIGIN_JITTER = (0.0, 0.02)


class Aodv:
    """AODV-like wrapper matching Drone routing API (minimal features).

    Implements: hello sender, reverse-route install on RREQ, intermediate RREP when fresh route exists,
    basic RREQ broadcast from origin, and RREP forwarding. Not a full RFC implementation.
    """

    def __init__(self, simulator, my_drone):
        self.simulator = simulator
        self.my_drone = my_drone
        self.env = simulator.env
        self.route_table = RouteTable(self.env, my_drone, HELLO_INTERVAL)

        # RREQ duplicate suppression set and counters
        self.rreq_seen = set()
        self.rreq_id = 1
        self.dest_seqno = 1

        # start processes
        self.env.process(self._hello_sender())

    def _hello_sender(self):
        while True:
            # build hello packet and enqueue for broadcast
            config.GL_ID_HELLO_PACKET += 1
            channel_id = self.my_drone.channel_assigner.channel_assign()
            hello = AodvHelloPacket(src_drone=self.my_drone,
                                    creation_time=self.env.now,
                                    id_hello_packet=config.GL_ID_HELLO_PACKET,
                                    hello_packet_length=config.HELLO_PACKET_LENGTH,
                                    simulator=self.simulator,
                                    channel_id=channel_id)
            hello.transmission_mode = 1
            self.my_drone.transmitting_queue.put(hello)
            self.simulator.metrics.control_packet_num += 1
            yield self.env.timeout(HELLO_INTERVAL + random.uniform(0, 1000))

    def next_hop_selection(self, packet):
        # Check for a cached route
        dst = packet.dst_drone.identifier
        entry = self.route_table.get_route(dst)
        if entry is not None:
            packet.next_hop_id = entry['next_hop']
            return True, packet, False

        # No route: initiate RREQ as control packet and buffer the data at origin
        # Create an RREQ packet object and ask Drone to transmit it (enquire=True)
        config.GL_ID_HELLO_PACKET += 1
        channel_id = self.my_drone.channel_assigner.channel_assign()
        rreq = RREQPacket(origin=self.my_drone.identifier,
                          rreq_id=self.rreq_id,
                          dst_id=dst,
                          dst_seq_req=0,
                          hop_count=0,
                          path=[self.my_drone.identifier],
                          creation_time=self.env.now,
                          packet_id=config.GL_ID_HELLO_PACKET,
                          simulator=self.simulator,
                          channel_id=channel_id)
        rreq.transmission_mode = 1
        self.rreq_id += 1
        # the origin should buffer the data; Drone.feed_packet will append to waiting_list
        self.simulator.metrics.control_packet_num += 1
        return False, rreq, True

    def packet_reception(self, packet, src_drone_id):
        """Generator: handle incoming control/data packets delivered by Drone.receive()."""
        current_time = self.env.now

        # HELLO
        if isinstance(packet, AodvHelloPacket):
            # update route table for direct neighbor
            nid = packet.src_drone.identifier
            self.route_table.add_direct_neighbor(nid)
            logger.info( 
                "At time: %s (us) ---- UAV: %s received HELLO from neighbor: %s. Added/updated direct route.",
                current_time, self.my_drone.identifier, nid
            )

        # RREQ
        elif isinstance(packet, RREQPacket):
            key = (packet.origin, packet.rreq_id)
            if key in self.rreq_seen:
                logger.info(
                    "At time: %s (us) ---- UAV: %s received duplicate RREQ (origin: %s, id: %s) -> dropped.",
                    current_time, self.my_drone.identifier, packet.origin, packet.rreq_id
                )
                return
            self.rreq_seen.add(key)
            logger.info(
                "At time: %s (us) ---- UAV: %s received new RREQ from: %s (origin: %s, dst: %s, hop_count: %s)",
                current_time, self.my_drone.identifier, src_drone_id,
                packet.origin, packet.dst, packet.hop_count
            )

            # install reverse route to origin via src_drone_id
            self.route_table.install_route(packet.origin, src_drone_id, dest_seq=0, hop_count=packet.hop_count + 1, refresh_only=True)


            # if I'm destination
            if self.my_drone.identifier == packet.dst:
                self.dest_seqno += 1
                rep_dst_seq = self.dest_seqno
                rep_hops = 0
                # create RREP and send back to previous hop
                config.GL_ID_HELLO_PACKET += 1
                channel_id = self.my_drone.channel_assigner.channel_assign()
                rrep = RREPPacket(rep_src=self.my_drone.identifier,
                                   origin=packet.origin,
                                   rep_dst_seq=rep_dst_seq,
                                   rep_hops=rep_hops,
                                   rep_path=list(packet.path) + [self.my_drone.identifier],
                                   creation_time=self.env.now,
                                   packet_id=config.GL_ID_HELLO_PACKET,
                                   simulator=self.simulator,
                                   channel_id=channel_id)
                # send unicast back to the neighbor that forwarded the RREQ
                # set unicast next hop (the previous hop that delivered the RREQ)
                rrep.next_hop_id = src_drone_id
                rrep.transmission_mode = 0
                self.my_drone.transmitting_queue.put(rrep)
                self.simulator.metrics.control_packet_num += 1
                return

            # intermediate: if fresh route to dst, reply
            entry = self.route_table.get_route(packet.dst)
            if entry is not None and entry.get('seq', 0) >= packet.dst_seq_req and entry.get('seq', 0) != 0:
                rep_dst_seq = entry.get('seq', 0)
                rep_hops = entry.get('hops', 0)
                config.GL_ID_HELLO_PACKET += 1
                channel_id = self.my_drone.channel_assigner.channel_assign()
                rrep = RREPPacket(rep_src=packet.dst,
                                   origin=packet.origin,
                                   rep_dst_seq=rep_dst_seq,
                                   rep_hops=rep_hops,
                                   rep_path=list(packet.path) + [self.my_drone.identifier],
                                   creation_time=self.env.now,
                                   packet_id=config.GL_ID_HELLO_PACKET,
                                   simulator=self.simulator,
                                   channel_id=channel_id)
                # reply unicast back to the neighbor who sent this RREQ
                rrep.next_hop_id = src_drone_id
                rrep.transmission_mode = 0
                self.my_drone.transmitting_queue.put(rrep)
                self.simulator.metrics.control_packet_num += 1
                return

            # otherwise, rebroadcast RREQ to neighbors (exclude the src)
            new_hop = packet.hop_count + 1
            new_path = list(packet.path) + [self.my_drone.identifier]
            for n in list(self.my_drone.channel_assigner.simulator.drones):
                # do nothing here: actual broadcasting is done by Drone/MAC when packet is queued
                pass

        # RREP
        elif isinstance(packet, RREPPacket):
            # install forward route to rep_src via src_drone_id
            self.route_table.install_route(packet.rep_src, src_drone_id, dest_seq=packet.rep_dst_seq, hop_count=packet.rep_hops + 1)
            logger.info(
                "At time: %s (us) ---- UAV: %s received RREP from: %s (origin: %s, dst_seq: %s, hops: %s). "
                "Installed forward route via neighbor: %s",
                current_time, self.my_drone.identifier, packet.rep_src, packet.origin,
                packet.rep_dst_seq, packet.rep_hops + 1, src_drone_id
            )

            # if I'm the origin, flush waiting list
            if self.my_drone.identifier == packet.origin:
                # move any waiting packets for rep_src into transmitting_queue
                for m in list(self.my_drone.waiting_list):
                    if m.dst_drone.identifier == packet.rep_src:
                        try:
                            self.my_drone.transmitting_queue.put(m)
                            self.my_drone.waiting_list.remove(m)
                        except ValueError:
                            pass
                return
            else:
                # forward RREP toward origin using reverse route if exists
                rev = self.route_table.get_route(packet.origin)
                if rev is not None:
                    next_hop = rev.get('next_hop')
                    # forward RREP toward origin using reverse route (unicast)
                    packet.next_hop_id = next_hop
                    packet.transmission_mode = 0
                    self.my_drone.transmitting_queue.put(packet)

                # DATA
        elif isinstance(packet, DataPacket):
            pkt = copy.copy(packet)  # keep original safe
            dst_id = pkt.dst_drone.identifier
            me = self.my_drone.identifier

            # If I'm the destination: deliver locally, update metrics, NO network-layer ACK
            if dst_id == me:
                if pkt.packet_id not in self.simulator.metrics.datapacket_arrived:
                    self.simulator.metrics.calculate_metrics(pkt)
                    logger.info(
                        "At time: %s (us) ---- UAV: %s received DATA (id: %s) as DESTINATION",
                        current_time, me, pkt.packet_id
                    )
                # nothing else to do for AODV; MAC-layer ACK already handled at link layer
                yield self.env.timeout(1)
                return

            # I'm an intermediate forwarder
            # Look up a forward route to the final destination
            entry = self.route_table.get_route(dst_id)
            if entry is not None:
                next_hop = entry.get('next_hop')
                if next_hop is None:
                    logger.info(
                        "At time: %s (us) ---- UAV: %s has route entry to %s but no next_hop; buffering and discovering",
                        current_time, me, dst_id
                    )
                else:
                    # Avoid trivial bounce back to the previous hop
                    if next_hop == src_drone_id:
                        logger.info(
                            "At time: %s (us) ---- UAV: %s forward route to %s points back to src %s; buffering & rediscover",
                            current_time, me, dst_id, src_drone_id
                        )
                    else:
                        # Refresh route lifetime on use (if your table supports touch)
                        try:
                            self.route_table.touch(dst_id)
                        except Exception:
                            pass

                        # Forward unicast toward next hop via MAC
                        pkt.next_hop_id = next_hop
                        pkt.transmission_mode = 0  # unicast
                        self.my_drone.transmitting_queue.put(pkt)
                        logger.info(
                            "At time: %s (us) ---- UAV: %s FORWARD DATA (id: %s) toward dst %s via next_hop %s",
                            current_time, me, pkt.packet_id, dst_id, next_hop
                        )
                        yield self.env.timeout(1)
                        return

            # No fresh route: buffer and trigger route discovery (once per (me,dst) pending)
            if self.my_drone.transmitting_queue.qsize() < self.my_drone.max_queue_size:
                self.my_drone.waiting_list.append(pkt)
                logger.info(
                    "At time: %s (us) ---- UAV: %s NO ROUTE to dst %s; buffered DATA (id: %s) and will RREQ",
                    current_time, me, dst_id, pkt.packet_id
                )
                # Initiate RREQ if not already sent for this (origin,dst) tuple
                if (me, dst_id) not in self.rreq_seen:
                    try:
                        self.rreq_seen.add((me, dst_id))
                    except AttributeError:
                        # initialize if missing
                        self.rreq_seen = set([(me, dst_id)])
                        
                    config.GL_ID_HELLO_PACKET += 1
                    channel_id = self.my_drone.channel_assigner.channel_assign()
                    rreq = RREQPacket(origin=self.my_drone.identifier,
                                    rreq_id=self.rreq_id,
                                    dst_id=dst_id,
                                    dst_seq_req=0,
                                    hop_count=0,
                                    path=[self.my_drone.identifier],
                                    creation_time=self.env.now,
                                    packet_id=config.GL_ID_HELLO_PACKET,
                                    simulator=self.simulator,
                                    channel_id=channel_id)
                    rreq.transmission_mode = 1
                    self.rreq_id += 1
                    self.my_drone.transmitting_queue.put(rreq)
                    # the origin should buffer the data; Drone.feed_packet will append to waiting_list
                    self.simulator.metrics.control_packet_num += 1
                    logger.info(
                        "At time: %s (us) ---- UAV: %s initiated RREQ for dst %s",
                        current_time, me, dst_id
                    )
            else:
                logger.info(
                    "At time: %s (us) ---- UAV: %s DROPPED DATA (id: %s); local queue full and no route",
                    current_time, me, pkt.packet_id
                )
        # keep generator style compatibility
        yield self.env.timeout(1)

    def penalize(self, packet):
        """
        Penalize a failed next-hop observed by MAC (e.g., ACK timeout).

        Current simple behavior: invalidate any cached routes that use the failed next-hop.
        This mirrors other routing modules in the project which at least provide the method
        to be called by the MAC layer.
        """
        next_hop = getattr(packet, 'next_hop_id', None)
        if next_hop is None:
            return

        # Remove any routes that rely on the failed neighbor
        try:
            self.route_table.invalidate_routes_through(next_hop)
            logger.info('At time: %s (us) ---- AODV: invalidated routes through failed next hop %s',
                        self.env.now, next_hop)
        except Exception:
            # keep penalize safe: do not raise from MAC's wait_ack
            return
