"""
Simple SimPy-based AODV-like simulator (lightweight educational demo)

Usage:
  pip install -r requirements.txt
  python simpy_simulator.py <num_nodes> <script_file>

The simulator intentionally simplifies many AODV details and focuses on
showing how to replace threads/timers/sockets with SimPy events:
- Nodes are SimPy processes
- Periodic hello messages are implemented using env.timeout
- Neighbor liveness and route lifetimes are simulated with scheduled events
- A very small RREQ/RREP mechanism is implemented (flood + reverse path)

This is a lightweight starting point — you can extend it to match the
full behavior in your threaded implementation.
"""

import sys
import simpy
import random
import os
import datetime

HELLO_INTERVAL = 10
HELLO_TIMEOUT = 30
ROUTE_LIFETIME = 300
NETWORK_DELAY = (1, 3)  # min/max delay for message delivery

# Global file handle for logging (opened in main)
LOG_FH = None

class Node:
    def __init__(self, env, node_id, network):
        self.env = env
        self.id = node_id
        self.network = network
        self.neighbors = set()
        self.routing_table = {}  # dest -> (next_hop, lifetime_event)
        self.message_box = []
        self.logs = []
        self.rreq_seen = set()  # (origin, rreq_id)
        self.pending_msgs = []
        self.seq = 0
        # starts a background process that continuously sends hello messages at fixed intervals in the simulation
        self.hello_proc = env.process(self._hello_sender())

    def log(self, text):
        entry = f"{self.env.now:>5.1f}: {text}"
        self.logs.append(entry)
        line = f"[{self.id}] {entry}"
        print(line)
        # also write to the global log file if available
        try:
            if LOG_FH is not None:
                LOG_FH.write(line + "\n")
                LOG_FH.flush()
        except Exception:
            # don't let logging errors break the simulation
            pass

    def _delay(self):
        return random.uniform(*NETWORK_DELAY)

    def _hello_sender(self):
        # Periodically send HELLO to neighbors (simulated)
        while True:
            yield self.env.timeout(HELLO_INTERVAL)
            for n in list(self.neighbors):
                self.network.send(self.id, n, ("HELLO", self.id))
            self.log(f"Sent HELLO to {list(self.neighbors)}")

    def add_neighbors(self, neighbors):
        for n in neighbors:
            self.neighbors.add(n)
            # install direct route
            self._install_route(n, n)
        self.log(f"Neighbors set -> {sorted(self.neighbors)}")

    def _install_route(self, dest, next_hop):
        # cancel old lifetime if exists
        if dest in self.routing_table:
            ev = self.routing_table[dest][1]
            if ev and not ev.triggered:
                ev.interrupt('replace')
        # schedule lifetime expiry
        lifetime = self.env.process(self._route_lifetime(dest))
        self.routing_table[dest] = (next_hop, lifetime)

    def _route_lifetime(self, dest):
        try:
            yield self.env.timeout(ROUTE_LIFETIME)
            # expire
            if dest in self.routing_table:
                del self.routing_table[dest]
                self.log(f"Route to {dest} expired")
        except simpy.Interrupt:
            # replaced or refreshed
            return

    def receive(self, src, payload):
        typ = payload[0]
        if typ == 'HELLO':
            # refresh neighbor liveness and route
            self.log(f"Received HELLO from {src}")
            if src not in self.neighbors:
                # treat as neighbor addition
                self.neighbors.add(src)
            self._install_route(src, src)
        elif typ == 'RREQ':
            (__, origin, rreq_id, dst, path) = payload
            key = (origin, rreq_id)
            if key in self.rreq_seen:
                return
            self.rreq_seen.add(key)
            # record reverse path
            reverse_next = path[-1] if path else src
            self._install_route(origin, src)
            self.log(f"RREQ for {dst} from {origin}, path={path}")
            if self.id == dst:
                # send RREP back along reverse path
                self.log(f"I am dest {dst}; sending RREP to {origin}")
                self.network.send(self.id, src, ("RREP", self.id, origin, list(path)+[self.id]))
            else:
                # forward RREQ
                new_path = list(path) + [self.id]
                for n in list(self.neighbors):
                    if n != src:
                        self.network.send(self.id, n, ("RREQ", origin, rreq_id, dst, new_path))
        elif typ == 'RREP':
            (_, rep_src, origin, rep_path) = payload
            self.log(f"RREP received from {rep_src} for {origin}; path={rep_path}")
            # install route to rep_src via src
            self._install_route(rep_src, src)
            # if I'm the origin, route established; otherwise forward back
            if self.id == origin:
                self.log(f"Route to {rep_src} established at origin {origin}")
                # send any pending messages
                to_send = [m for m in self.pending_msgs if m[0]==rep_src]
                for m in to_send:
                    self._send_user_message(m[1], rep_src, m[2])
                    self.pending_msgs.remove(m)
            else:
                # forward towards origin using routing table
                if origin in self.routing_table:
                    next_hop = self.routing_table[origin][0]
                    self.network.send(self.id, next_hop, payload)
        elif typ == 'MSG':
            (_, origin, dest, msg) = payload
            if dest == self.id:
                self.message_box.append((origin, msg))
                self.log(f"Message received from {origin}: {msg}")
            else:
                # forward if route exists
                if dest in self.routing_table:
                    nh = self.routing_table[dest][0]
                    self.network.send(self.id, nh, payload)
                else:
                    # initiate RREQ using per-node seq id
                    rreq_id = self.seq
                    self.seq += 1
                    self.log(f"No route to {dest}; broadcasting RREQ")
                    for n in list(self.neighbors):
                        self.network.send(self.id, n, ("RREQ", self.id, rreq_id, dest, [self.id]))
                    # buffer message
                    self.pending_msgs.append((dest, self.id, msg))

    def _send_user_message(self, source, dest, msg):
        # used to send buffered messages after route discovery
        payload = ("MSG", source, dest, msg)
        if dest in self.routing_table:
            nh = self.routing_table[dest][0]
            self.network.send(self.id, nh, payload)
        else:
            # initiate route discovery from origin node and buffer the message
            rreq_id = self.seq
            self.seq += 1
            self.log(f"No route to {dest}; origin broadcasting RREQ")
            for n in list(self.neighbors):
                self.network.send(self.id, n, ("RREQ", self.id, rreq_id, dest, [self.id]))
            # buffer message so it will be sent when route is found
            self.pending_msgs.append((dest, self.id, msg))

    # CLI-like helpers used by the script runner
    def show_route(self):
        self.log(f"Routing table: { {k:v[0] for k,v in self.routing_table.items()} }")

    def show_messages(self):
        self.log(f"Messages: {self.message_box}")

    def show_log(self):
        print("\n".join(self.logs))

class Network:
    def __init__(self, env):
        self.env = env
        self.nodes = {}

    def add_node(self, node_id):
        self.nodes[node_id] = Node(self.env, node_id, self)

    def send(self, src, dst, payload):
        # simulate network delay
        if dst not in self.nodes:
            return
        delay = random.uniform(*NETWORK_DELAY)
        # schedule delivery
        def deliver(env, delay, dst, src, payload):
            yield env.timeout(delay)
            # deliver
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

    # Small helper to map 'n1'.. to node ids
    def get_node(n):
        return n

    for line in lines:
        tokens = line.split()
        # support optional leading time/token: if first token is numeric treat it as time and strip it
        if tokens and tokens[0].isdigit():
            tokens = tokens[1:]
        if not tokens:
            continue
        cmd = tokens[0]
        if cmd == 'add_neighbors':
            # expected: add_neighbors <neighbor> to <target>
            if len(tokens) >= 4 and tokens[2] == 'to':
                neighbor = tokens[1]
                target = tokens[3]
                env.process(_run_at(env, network, 0, lambda neighbor=neighbor, target=target: network.nodes[target].add_neighbors([neighbor])))
            else:
                print('Malformed add_neighbors line:', line)
        elif cmd == 'show_route':
            if len(tokens) >= 2:
                target = tokens[1]
                env.process(_run_at(env, network, 0, lambda target=target: network.nodes[target].show_route()))
            else:
                print('Malformed show_route line:', line)
        elif cmd == 'send_message':
            # send_message <src> to <dst> <msg-with-@>
            if len(tokens) >= 4 and tokens[2] == 'to':
                src = tokens[1]
                dst = tokens[3]
                msg = ' '.join(tokens[4:]) if len(tokens) > 4 else ''
                msg = ' '.join(msg.split('@'))
                env.process(_run_at(env, network, 0, lambda s=src, d=dst, m=msg: network.nodes[s]._send_user_message(s, d, m)))
            else:
                print('Malformed send_message line:', line)
        elif cmd == 'show_messages':
            if len(tokens) >= 2:
                target = tokens[1]
                env.process(_run_at(env, network, 0, lambda target=target: network.nodes[target].show_messages()))
            else:
                print('Malformed show_messages line:', line)
        elif cmd == 'show_log':
            if len(tokens) >= 2:
                target = tokens[1]
                env.process(_run_at(env, network, 0, lambda target=target: network.nodes[target].show_log()))
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
    network = Network(env)
    for i in range(n):
        node_id = f'n{i+1}'
        network.add_node(node_id)

    # run the script as a process
    env.process(run_script(env, network, n, script))

    # run the simulation for a reasonable amount of simulated time
    env.run(until=200)

    # close log file if opened
    try:
        if LOG_FH is not None:
            LOG_FH.write('---\nSimulation finished.\n')
            LOG_FH.close()
            print('Log saved.')
    except Exception:
        pass

if __name__ == '__main__':
    main()
