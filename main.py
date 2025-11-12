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

if __name__ == "__main__":
    # Simulation setup
    env = simpy.Environment()
    channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
    sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)

    # ====== Physical Layer Setup ================
    # Profile options: wifi_11n, wifi_11ac, wifi_direct
    selected_profile = wifi_11ac
    sim.channel = create_channel(env, selected_profile)
    print(f"Using channel: {type(sim.channel).__name__} with loss_prob={getattr(sim.channel, 'loss_prob', None)}")
    print(f"Using tech profile: {selected_profile.name}")

    # Register inboxes for all drones BEFORE any packet send
    for drone_id in range(config.NUMBER_OF_DRONES):
        sim.channel.create_inbox_for_receiver(drone_id)

    # TEST BLOCK to verify packet loss
    '''print("\n[TEST] Sending a test broadcast...")
    sim.channel.broadcast_put(["test_packet", 123, "droneX"])
    print("[TEST] UAV inbox states after broadcast:")
    for uav_id in range(config.NUMBER_OF_DRONES):
        print(f"UAV {uav_id} inbox:", sim.channel.pipes[uav_id])
    print("\n[TEST] Sending a test unicast...")
    sim.channel.unicast_put(["test_packet", 124, "droneY"], 1)
    print("UAV 1 inbox after unicast:", sim.channel.pipes[1])
    print("\n")  # End of test block'''

    # Add the visualizer to the simulator
    # Use 20000 microseconds (0.02s) as the visualization frame interval
    visualizer = SimulationVisualizer(sim, output_dir=".", vis_frame_interval=20000)
    visualizer.run_visualization()

    # Run simulation
    env.run(until=config.SIM_TIME)
    
    # Finalize visualization
    visualizer.finalize()
