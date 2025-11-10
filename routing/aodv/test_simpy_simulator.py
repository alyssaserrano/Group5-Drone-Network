# test_simpy_simulator_full.py
import pytest
import simpy
import random
import simpy_sim_2 as ss

# Fix randomness for reproducibility
random.seed(42)

# -------------------
# Node Initialization
# -------------------
def test_node_init():
    env = simpy.Environment()
    network = ss.MAC(env)
    network.add_node("n1")
    node = network.nodes["n1"]

    assert node.id == "n1"
    assert node.neighbors == set()
    assert node.routing_table == {}
    assert node.message_box == []
    assert node.rreq_id == 1
    assert node.dest_seqno == 1
    assert isinstance(node.hello_proc, simpy.events.Process)
    assert isinstance(node.neighbor_monitor, simpy.events.Process)

# -------------------
# Utilities
# -------------------
def test_install_route_full_and_direct_neighbor():
    env = simpy.Environment()
    network = ss.MAC(env)
    network.add_node("n1")
    node = network.nodes["n1"]

    # Direct neighbor installation
    node._install_direct_neighbor("n2")
    assert "n2" in node.routing_table
    assert node.routing_table["n2"][0] == "n2"
    assert node.routing_table["n2"][3] == 1  # hop_count=1

    # Installing a new route should replace old
    node._install_route_full("n2", "n3", dest_seq=1, hop_count=0)
    new_entry = node.routing_table["n2"]
    assert new_entry[0] == "n3"
    assert new_entry[2] == 1  # seqnum updated
    assert new_entry[3] == 0  # hop count updated

def test_route_lifetime_expiration():
    env = simpy.Environment()
    network = ss.MAC(env)
    network.add_node("n1")
    node = network.nodes["n1"]

    # install route and check it expires
    node._install_route_full("n2", "n2")
    assert "n2" in node.routing_table

    env.run(until=ss.ROUTE_LIFETIME + 1)
    assert "n2" not in node.routing_table

def test_invalidate_routes_through():
    env = simpy.Environment()
    network = ss.MAC(env)
    network.add_node("n1")
    node = network.nodes["n1"]

    node._install_route_full("d1", "n2")
    node._install_route_full("d2", "n2")
    node._install_route_full("d3", "n3")

    node._invalidate_routes_through("n2")
    assert "d1" not in node.routing_table
    assert "d2" not in node.routing_table
    assert "d3" in node.routing_table

# -------------------
# Network send/receive
# -------------------
def test_message_send_receive():
    env = simpy.Environment()
    network = ss.MAC(env)
    network.add_node("n1")
    network.add_node("n2")

    n1 = network.nodes["n1"]
    n2 = network.nodes["n2"]

    n1.add_neighbors(["n2"])
    n2.add_neighbors(["n1"])

    # Send message
    n1._send_user_message("n1", "n2", "Hello")
    env.run(until=5)
    assert ("n1", "Hello") in n2.message_box

# -------------------
# RREQ / RREP flow
# -------------------
def test_rreq_rrep():
    env = simpy.Environment()
    network = ss.MAC(env)
    for i in range(3):
        network.add_node(f"n{i+1}")

    n1 = network.nodes["n1"]
    n2 = network.nodes["n2"]
    n3 = network.nodes["n3"]

    # Linear topology
    n1.add_neighbors(["n2"])
    n2.add_neighbors(["n1", "n3"])
    n3.add_neighbors(["n2"])

    # Trigger route discovery
    n1._send_user_message("n1", "n3", "msg")
    env.run(until=50)

    assert ("n1", "msg") in n3.message_box
    assert "n3" in n1.routing_table

# -------------------
# HELLO and neighbor monitor
# -------------------
def test_hello_and_neighbor_monitor():
    env = simpy.Environment()
    network = ss.MAC(env)
    network.add_node("n1")
    network.add_node("n2")

    n1 = network.nodes["n1"]
    n2 = network.nodes["n2"]

    n1.add_neighbors(["n2"])
    n2.add_neighbors(["n1"])

    # simulate HELLO sending & timeout
    env.run(until=ss.HELLO_INTERVAL + 0.1)
    assert "n2" in n1.neighbors
    assert "n1" in n2.neighbors

    # manually simulate timeout
    n2.hello_proc.interrupt() # Stop n2 from sending HELLOs
    env.run(until=env.now + ss.HELLO_INTERVAL + 1) # Allow time for last HELLO to be processed
    n1.last_hello["n2"] = env.now - ss.HELLO_TIMEOUT # Force timeout
    env.run(until=env.now + ss.HELLO_INTERVAL + 1) # now advance time to trigger neighbor monitor
    assert "n2" not in n1.neighbors

# -------------------
# Script runner functions
# -------------------
def test_run_script_add_neighbors(tmp_path):
    script_file = tmp_path / "script.txt"
    script_file.write_text("add_neighbors n2 to n1\nshow_route n1")

    env = simpy.Environment()
    network = ss.MAC(env)
    network.add_node("n1")
    network.add_node("n2")

    env.process(ss.run_script(env, network, 2, str(script_file)))
    env.run(until=10)

    # Check that route installed
    n1 = network.nodes["n1"]
    assert "n2" in n1.routing_table

# -------------------
# _run_at helper
# -------------------
def test_run_at_helper_called():
    env = simpy.Environment()
    called = []

    def f():
        called.append(1)

    env.process(ss._run_at(env, None, 1, f))
    env.run(until=2)
    assert called == [1]


def test_multiple_rrep_handling():
    env = simpy.Environment()
    network = ss.MAC(env)

    # Create nodes
    network.add_node("A")
    network.add_node("B")
    network.add_node("C")
    network.add_node("D")

    A = network.nodes["A"]
    B = network.nodes["B"]
    C = network.nodes["C"]
    D = network.nodes["D"]

    # Topology:
    # A - B - C - D
    A.add_neighbors(["B"])
    B.add_neighbors(["A", "C"])
    C.add_neighbors(["B", "D"])
    D.add_neighbors(["C"])

    # Simulate two different paths from D to A
    # Path1: D -> C -> B -> A
    # Path2: D -> C -> A (we'll inject an artificial neighbor link)
    C.add_neighbors(["A"])  # Shortcut to A

    # Trigger A sending message to D (this generates RREQ)
    A._send_user_message("A", "D", "Hello D")
    
    # Run the simulation for enough time for RREQ/RREP
    env.run(until=50)

    # After multiple RREPs, A should have a route to D
    assert "D" in A.routing_table

    # The route should be via the **first RREP received**, not overwritten by duplicate
    next_hop = A.routing_table["D"][0]
    assert next_hop in {"B", "C"}  # Depending on which RREP arrived first

    # Check the message arrived at D
    assert ("A", "Hello D") in D.message_box

    # There should be **no further updates** from duplicate RREPs
    initial_seq = A.routing_table["D"][1]  # dest_seq
    initial_hop = A.routing_table["D"][3]  # hop count

    # Run more simulation time to allow duplicates to arrive
    env.run(until=100)
    
    # Route info should not change
    assert A.routing_table["D"][1] == initial_seq
    assert A.routing_table["D"][3] == initial_hop