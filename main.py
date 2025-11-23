import simpy
from utils import config
from simulator.simulator import Simulator
from visualization.visualizer import SimulationVisualizer

# Physical Layer
from phy.tech_profiles import wifi_11n
from phy.tech_profiles import wifi_11ac
from phy.tech_profiles import wifi_direct
from phy.channel_create import create_channel

"""
  _   _                   _   _          _     ____    _             
 | | | |   __ _  __   __ | \ | |   ___  | |_  / ___|  (_)  _ __ ___  
 | | | |  / _` | \ \ / / |  \| |  / _ \ | __| \___ \  | | | '_ ` _ \ 
 | |_| | | (_| |  \ V /  | |\  | |  __/ | |_   ___) | | | | | | | | |
  \___/   \__,_|   \_/   |_| \_|  \___|  \__| |____/  |_| |_| |_| |_|
                                                                                                                                                                                                                                                                                           
"""
# MAC layer integration testing
def print_mac_integration_test(sim):
    """Quick MAC layer verification"""
    print("\n" + "=" * 80)
    print("MAC LAYER VERIFICATION")
    print("=" * 80)

    # Test 1: Check initialization
    print("\n Testing Initialization...")
    for drone in sim.drones:
        mac = drone.mac_protocol
        print(f"  Drone {drone.identifier}: {mac.role.name}")

    # Test 2: Check beacons
    print("\n Testing Beacons...")
    for drone in sim.drones:
        if drone.mac_protocol.role.name == "COMMAND_CONTROL":
            metrics = drone.mac_protocol.get_metrics()
            beacons = metrics.get('tx_beacon_frames', 0)
            print(f"  C&C Drone {drone.identifier}: {beacons} beacons sent")

    # Test 3: Check neighbor discovery
    print("\n Testing Neighbor Discovery...")
    for drone in sim.drones:
        if drone.mac_protocol.role.name == "WORKER_DRONE":
            neighbors = drone.mac_protocol.get_neighbors()
            print(f"  Worker {drone.identifier}: {len(neighbors)} neighbors found")

    # Test 4: Check data transmission
    print("\n Testing Data Transmission...")
    total_tx = sum(d.mac_protocol.get_metrics()['data_tx_frames'] for d in sim.drones)
    total_rx = sum(d.mac_protocol.get_metrics()['data_rx_frames'] for d in sim.drones)
    print(f"  Network Total: TX={total_tx}, RX={total_rx}")

    # Verdict
    print("\n" + "=" * 80)
    if total_tx > 0 and total_rx > 0:
        print("MAC LAYER: WORKING")
    else:
        print("MAC LAYER: CHECK RESULTS ABOVE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    # Simulation setup
    env = simpy.Environment()
    channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
    sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
    
    # Add the visualizer to the simulator
    # Use 20000 microseconds (0.02s) as the visualization frame interval
    visualizer = SimulationVisualizer(sim, output_dir=".", vis_frame_interval=20000)
    visualizer.run_visualization()

    # Run simulation
    env.run(until=config.SIM_TIME)

    # Test MAC code
    print_mac_integration_test(sim)

    # Debug: Print final energy levels of all drones
    for drone in sim.drones:
        print(f"Drone {drone.identifier} final energy: {drone.residual_energy}")
    
    # Finalize visualization
    visualizer.finalize()
