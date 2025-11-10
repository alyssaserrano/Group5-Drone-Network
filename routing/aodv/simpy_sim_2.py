"""
Simple SimPy-based AODV-like simulator (lightweight educational demo, corrected)

Usage:
  pip install -r requirements.txt
  python simpy_simulator.py <num_nodes> <script_file>

Major notes vs. RFC 3561:
- Still simplified: no RERR/precursors/local repair/expanding ring TTL/rate limiting.
- Implements per-destination seqno freshness + hop-count update rule.
- Allows intermediate RREP if cached route is fresh enough.
"""

import sys
import simpy
import random
import os
import datetime

HELLO_INTERVAL = 10
HELLO_TIMEOUT  = 30
ROUTE_LIFETIME = 300
NETWORK_DELAY  = (1, 3)     # min/max delay for link delivery
REBROADCAST_JITTER = (0.0, 0.05)
ORIGIN_JITTER      = (0.0, 0.02)

# Global file handle for logging (opened in main)
LOG_FH = None

class Node:
    def __init__(self, env, node_id, mac):
        self.env = env
        self.id = node_id
        self.mac = mac

        self.neighbors = set()
        # routing_table: dest -> (next_hop, lifetime_event, dest_seq, hop_count, precursors_set)
        self.routing_table = {}
        self.message_box = []
        self.logs = []

        # RREQ duplicate suppression: (origin, rreq_id)
        self.rreq_seen = set()
        # buffered data while discovering routes: list of (dest, source, msg)
        self.pending_msgs = []

        # Per-node counters
        self.rreq_id = 1      # unique per-origin request IDs
        self.dest_seqno = 1   # this node's own destination sequence number (for RREP about self)

        # For HELLO timeout
        self.last_hello = {}

        # background processes
        self.hello_proc = env.process(self._hello_sender())
        self.neighbor_monitor = env.process(self._neighbor_monitor())

    # ---------- utilities ----------

    def log(self, text):
        entry = f"{self.env.now:>5.1f}: {text}"
        self.logs.append(entry)
        line = f"[{self.id}] {entry}"
        print(line)
        try:
            if LOG_FH is not None:
                LOG_FH.write(line + "\n")
                LOG_FH.flush()
        except Exception:
            pass

    def _route_lifetime(self, dest):
        """Expire a route after ROUTE_LIFETIME unless refreshed/replaced."""
        try:
            yield self.env.timeout(ROUTE_LIFETIME)
            if dest in self.routing_table:
                del self.routing_table[dest]
                self.log(f"Route to {dest} expired")
        except simpy.Interrupt:
            # refreshed or replaced
            return

    def _install_route_full(self, dest, next_hop, dest_seq=0, hop_count=0, refresh_only=False):
        """
        Install/refresh route using AODV update rule:
        Accept new entry if:
          - dest not in the route table yet, OR
          - new_seq > old_seq, OR
          - new_seq == old_seq and new_hops < old_hops
        If not accepted, we still refresh lifetime if refresh_only=True.
        """
        old = self.routing_table.get(dest)

        # decide if we should replace
        should_replace = False
        if old is None:
            should_replace = True
        else:
            _, old_ev, old_seq, old_hops, old_prec = old
            if (dest_seq > old_seq) or (dest_seq == old_seq and hop_count < old_hops):
                should_replace = True

        if should_replace:
            # cancel old lifetime if exists
            if old is not None:
                old_ev = old[1]
                if old_ev and not old_ev.triggered:
                    old_ev.interrupt('replace')
                    self.log(f"Timer for route to {dest} cancelled due to replacement")

            lifetime = self.env.process(self._route_lifetime(dest))
            self.routing_table[dest] = (next_hop, lifetime, dest_seq, hop_count, set())
            self.log(f"Route to {dest} installed/updated via {next_hop} (seq={dest_seq}, hops={hop_count})")
            return self.routing_table[dest]

        # no replacement; optionally refresh lifetime
        if old is not None:
            old_next, old_ev, old_seq, old_hops, old_prec = old
            if old_ev and not old_ev.triggered:
                old_ev.interrupt('refresh')
            lifetime = self.env.process(self._route_lifetime(dest))
            self.routing_table[dest] = (old_next, lifetime, old_seq, old_hops, old_prec)
            return self.routing_table[dest]

        return None

    def _install_direct_neighbor(self, n):
        # consistent: direct neighbor hop_count = 1; dest_seq unknown(0)
        self._install_route_full(n, n, dest_seq=0, hop_count=1)

    def _delayed_send(self, dst, payload, delay):
        yield self.env.timeout(delay)
        self.mac.send(self.id, dst, payload)

    # ---------- periodic tasks ----------

    def _hello_sender(self):
        # Periodically send HELLO to known neighbors (simulated 1-hop beacons)
        try: 
            while True:
                yield self.env.timeout(HELLO_INTERVAL)
                for n in list(self.neighbors):
                    self.mac.send(self.id, n, ("HELLO", self.id))
                self.log(f"Sent HELLO to {sorted(self.neighbors)}")
        except simpy.Interrupt:
            self.log("HELLO sender interrupted (paused/stopped)")
            return

    def _neighbor_monitor(self):
        # prune neighbors that haven't sent HELLO within timeout; invalidate routes via them
        while True:
            yield self.env.timeout(HELLO_INTERVAL)
            now = self.env.now
            for n in list(self.neighbors):
                last = self.last_hello.get(n, None)
                if last is not None and (now - last) > HELLO_TIMEOUT:
                    try:
                        self.neighbors.remove(n)
                    except KeyError:
                        pass
                    # remove direct route if present
                    if n in self.routing_table and self.routing_table[n][0] == n:
                        del self.routing_table[n]
                    self.log(f"Neighbor {n} timed out and was removed (last heard={last})")
                    # invalidate any routes that used n as next hop
                    self._invalidate_routes_through(n)

    def _invalidate_routes_through(self, next_hop):
        to_delete = [d for d,entry in self.routing_table.items() if entry[0] == next_hop]
        for d in to_delete:
            del self.routing_table[d]
            self.log(f"Route to {d} invalidated because next-hop {next_hop} disappeared")

    # ---------- external API used by scripts ----------

    def add_neighbors(self, neighbors):
        for n in neighbors:
            self.neighbors.add(n)
            self._install_direct_neighbor(n)
        self.log(f"Neighbors set -> {sorted(self.neighbors)}")

    def show_route(self):
        self.log(f"Routing table: {{ {', '.join(f'{k}: {v[0]}' for k,v in self.routing_table.items())} }}")

    def show_messages(self):
        self.log(f"Messages: {self.message_box}")

    def show_log(self):
        print("\n".join(self.logs))

    # ---------- core protocol handlers ----------

    def receive(self, src, payload):
        typ = payload[0]

        if typ == 'HELLO':
            self.log(f"Received HELLO from {src}")
            self.last_hello[src] = self.env.now
            if src not in self.neighbors:
                self.neighbors.add(src)
            self._install_direct_neighbor(src)

        elif typ == 'RREQ':
            # ('RREQ', origin, rreq_id, dst, dst_seq_req, hop_count, path)
            (_, origin, rreq_id, dst, dst_seq_req, hop_count, path) = payload
            key = (origin, rreq_id)
            if key in self.rreq_seen:
                return
            self.rreq_seen.add(key)

            # install/refresh reverse route to origin via src; hop_count is from origin->prev, we are one more hop away
            self._install_route_full(origin, src, dest_seq=0, hop_count=hop_count+1, refresh_only=True)

            self.log(f"RREQ for {dst} from {origin}, dst_seq_req={dst_seq_req}, hop={hop_count}, path={path}")

            if self.id == dst:
                # Destination replies (bump our own dest_seqno to advertise freshness)
                self.dest_seqno += 1
                rep_dst_seq = self.dest_seqno
                rep_hops = 0
                self.log(f"I am dest {dst}; sending RREP to {origin} (seq={rep_dst_seq})")
                # ('RREP', rep_src(=dst), origin, rep_dst_seq, rep_hops, rep_path)
                self.mac.send(self.id, src, ("RREP", self.id, origin, rep_dst_seq, rep_hops, list(path)+[self.id]))
                return

            # Intermediate node: if we have a fresh route to dst, we may reply
            entry = self.routing_table.get(dst)
            if entry is not None:
                (next_hop, _, entry_seq, entry_hops, _) = entry
                if entry_seq >= dst_seq_req and entry_seq != 0:
                    rep_dst_seq = entry_seq
                    rep_hops = entry_hops
                    self.log(f"Intermediate {self.id} replies for {dst} (seq={entry_seq}, hops={entry_hops}) to {origin}")
                    self.mac.send(self.id, src, ("RREP", dst, origin, rep_dst_seq, rep_hops, list(path)+[self.id]))
                    return

            # Otherwise, rebroadcast with jitter, increment hop, extend path
            new_hop = hop_count + 1
            new_path = list(path) + [self.id]
            for n in list(self.neighbors):
                if n != src:
                    jitter = random.uniform(*REBROADCAST_JITTER)
                    self.env.process(self._delayed_send(n, ("RREQ", origin, rreq_id, dst, dst_seq_req, new_hop, new_path), jitter))

        elif typ == 'RREP':
            # ('RREP', rep_src(=dst), origin, rep_dst_seq, rep_hops, rep_path)
            (_, rep_src, origin, rep_dst_seq, rep_hops, rep_path) = payload
            self.log(f"RREP from {rep_src} for {origin}; dst_seq={rep_dst_seq}, hops={rep_hops}, path={rep_path}")

            # Install forward route to destination rep_src via src; our hop to dest = rep_hops + 1
            self._install_route_full(rep_src, src, dest_seq=rep_dst_seq, hop_count=rep_hops+1)

            if self.id == origin:
                self.log(f"Route to {rep_src} established at origin {origin}")
                # Flush buffered messages for this destination
                to_send = [m for m in list(self.pending_msgs) if m[0] == rep_src]
                for m in to_send:
                    self._send_user_message(m[1], rep_src, m[2])
                    try:
                        self.pending_msgs.remove(m)
                    except ValueError:
                        pass
            else:
                # Forward RREP back toward origin using reverse route
                if origin in self.routing_table:
                    next_hop = self.routing_table[origin][0]
                    self.mac.send(self.id, next_hop, payload)

        elif typ == 'MSG':
            # ('MSG', origin, dest, msg)
            (_, origin, dest, msg) = payload
            if dest == self.id:
                self.message_box.append((origin, msg))
                self.log(f"Message received from {origin}: {msg}")
            else:
                # forward if route exists
                if dest in self.routing_table:
                    nh = self.routing_table[dest][0]
                    self.mac.send(self.id, nh, payload)
                else:
                    # initiate route discovery and buffer
                    rreq_id = self.rreq_id
                    self.rreq_id += 1
                    # advertise requested dest seq if we have one cached
                    dst_entry = self.routing_table.get(dest)
                    dst_seq_req = dst_entry[2] if dst_entry is not None else 0
                    self.log(f"No route to {dest}; broadcasting RREQ (dst_seq_req={dst_seq_req})")
                    for n in list(self.neighbors):
                        jitter = random.uniform(*ORIGIN_JITTER)
                        # initial hop_count=0, path contains origin
                        self.env.process(self._delayed_send(n, ("RREQ", self.id, rreq_id, dest, dst_seq_req, 0, [self.id]), jitter))
                    self.pending_msgs.append((dest, self.id, msg))

    # ---------- app helper ----------

    def _send_user_message(self, source, dest, msg):
        """Called by the origin to (re)send a buffered message after route discovery."""
        payload = ("MSG", source, dest, msg)
        if dest in self.routing_table:
            nh = self.routing_table[dest][0]
            self.mac.send(self.id, nh, payload)
        else:
            # begin discovery if route still missing
            rreq_id = self.rreq_id
            self.rreq_id += 1
            dst_entry = self.routing_table.get(dest)
            dst_seq_req = dst_entry[2] if dst_entry is not None else 0
            self.log(f"No route to {dest}; origin broadcasting RREQ (dst_seq_req={dst_seq_req})")
            for n in list(self.neighbors):
                jitter = random.uniform(*ORIGIN_JITTER)
                self.env.process(self._delayed_send(n, ("RREQ", self.id, rreq_id, dest, dst_seq_req, 0, [self.id]), jitter))
            self.pending_msgs.append((dest, self.id, msg))


class MAC:
    def __init__(self, env):
        self.env = env
        self.nodes = {}

    def add_node(self, node_id):
        self.nodes[node_id] = Node(self.env, node_id, self)

    def send(self, src, dst, payload):
        if dst not in self.nodes:
            return
        delay = random.uniform(*NETWORK_DELAY)
        def deliver(env, delay, dst, src, payload):
            yield env.timeout(delay)
            self.nodes[dst].receive(src, payload)
        self.env.process(deliver(self.env, delay, dst, src, payload))


def run_script(env, network, num_nodes, script_file):
    # Read script
    try:
        with open(script_file, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print('Script file not found:', script_file)
        return

    def get_node(n):  # keep for future expansion
        return n

    for line in lines:
        tokens = line.split()
        # optional leading numeric time token: if first token is numeric, strip it
        if tokens and tokens[0].isdigit():
            tokens = tokens[1:]
        if not tokens:
            continue

        cmd = tokens[0]
        if cmd == 'add_neighbors':
            # add_neighbors <neighbor> to <target>
            if len(tokens) >= 4 and tokens[2] == 'to':
                neighbor = tokens[1]
                target = tokens[3]
                env.process(_run_at(env, network, 0, lambda neighbor=neighbor, target=target:
                                    network.nodes[target].add_neighbors([neighbor])))
            else:
                print('Malformed add_neighbors line:', line)

        elif cmd == 'show_route':
            if len(tokens) >= 2:
                target = tokens[1]
                env.process(_run_at(env, network, 0, lambda target=target:
                                    network.nodes[target].show_route()))
            else:
                print('Malformed show_route line:', line)

        elif cmd == 'send_message':
            # send_message <src> to <dst> <msg-with-@>
            if len(tokens) >= 4 and tokens[2] == 'to':
                src = tokens[1]
                dst = tokens[3]
                msg = ' '.join(tokens[4:]) if len(tokens) > 4 else ''
                msg = ' '.join(msg.split('@'))
                env.process(_run_at(env, network, 0, lambda s=src, d=dst, m=msg:
                                    network.nodes[s]._send_user_message(s, d, m)))
            else:
                print('Malformed send_message line:', line)

        elif cmd == 'show_messages':
            if len(tokens) >= 2:
                target = tokens[1]
                env.process(_run_at(env, network, 0, lambda target=target:
                                    network.nodes[target].show_messages()))
            else:
                print('Malformed show_messages line:', line)

        elif cmd == 'show_log':
            if len(tokens) >= 2:
                target = tokens[1]
                env.process(_run_at(env, network, 0, lambda target=target:
                                    network.nodes[target].show_log()))
            else:
                print('Malformed show_log line:', line)

        else:
            print('Unknown command in script:', cmd)

        # advance simulation time a little between commands
        yield env.timeout(1)


def _run_at(env, network, delay, func):
    yield env.timeout(delay)
    func()


def main():
    if len(sys.argv) < 3:
        print('Usage: python simpy_simulator.py <num_nodes> <script_file>')
        sys.exit(1)
    n = int(sys.argv[1])
    script = sys.argv[2]

    # prepare log file
    global LOG_FH
    LOG_FH = None
    try:
        base = os.path.basename(script)
        ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        logname = f"simpy_sim_{base}_{ts}.log"
        LOG_FH = open(logname, 'w', encoding='utf-8')
        LOG_FH.write(f"SimPy AODV simulation log - script={script} run_at={ts}\n")
        LOG_FH.write('---\n')
        LOG_FH.flush()
        print(f"Logging simulation to {logname}")
    except Exception as e:
        print("Could not open log file:", e)

    env = simpy.Environment()
    network = MAC(env)
    for i in range(n):
        node_id = f'n{i+1}'
        network.add_node(node_id)

    # run the script as a process
    env.process(run_script(env, network, n, script))

    # run the simulation for a reasonable amount of simulated time
    env.run(until=200)

    try:
        if LOG_FH is not None:
            LOG_FH.write('---\nSimulation finished.\n')
            LOG_FH.close()
            print('Log saved.')
    except Exception:
        pass

if __name__ == '__main__':
    main()
