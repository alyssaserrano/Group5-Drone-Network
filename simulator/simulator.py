import random
import numpy as np
import matplotlib.pyplot as plt
from phy.prob_channel import ProbChannel
from phy.tech_profiles import wifi_direct
from entities.drone import Drone
from simulator.metrics import Metrics
from mobility import start_coords
from path_planning.astar import astar
from utils import config
from utils.util_function import grid_map
from allocation.central_controller import CentralController
from visualization.static_drawing import scatter_plot, scatter_plot_with_obstacles


class Simulator:
    """
    Description: simulation environment

    Attributes:
        env: simpy environment
        total_simulation_time: discrete time steps, in nanosecond
        n_drones: number of the drones
        channel_states: a dictionary, used to describe the channel usage
        channel: wireless channel
        metrics: Metrics class, used to record the network performance
        drones: a list, contains all drone instances

    Author: Zihao Zhou, eezihaozhou@gmail.com
    Created at: 2024/1/11
    Updated at: 2025/7/8
    """

    def __init__(self,
                 seed,
                 env,
                 channel_states,
                 n_drones,
                 total_simulation_time=config.SIM_TIME):

        self.env = env
        self.seed = seed
        self.total_simulation_time = total_simulation_time  # total simulation time (ns)

        self.n_drones = n_drones  # total number of drones in the simulation
        self.channel_states = channel_states
        # self.channel = Channel(self.env)
        self.channel = ProbChannel(self.env)  # using ProbChannel by default
        
        self.channel.simulator = self # Added 12/3/25

        self.metrics = Metrics(self)  # use to record the network performance

        
        # NOTE: if distributed optimization is adopted, remember to comment this to speed up simulation
        # self.central_controller = CentralController(self)

        ## start_position = start_coords.get_random_start_point_3d(seed) Original 12/3/25
        # start_position = start_coords.get_customized_start_point_3d()
        
        ############### Leader Follower expects specific offsets #12/3/25
        if config.MOBILITY_MODEL == "leader_follower":
            # Leader at middle, others near it
            cx, cy, cz = config.MAP_LENGTH/2, config.MAP_WIDTH/2, 50
            start_position = [
                [cx,     cy,     cz],      # leader
                [cx+50,  cy,     cz],      # follower 1
                [cx-50,  cy,     cz],      # follower 2
                [cx,     cy+50,  cz],      # follower 3
            ]
        else:
            start_position = start_coords.get_random_start_point_3d(seed)
        ###############

        self.drones = []
        print('Seed is: ', self.seed)
        for i in range(n_drones):
        #    if config.HETEROGENEOUS:          #12/3/25
        #        speed = random.randint(5, 60)
        #    else:
        #        speed = 10
            # ---------------- speed sweep selection ---------------- # #12/3/25
            if hasattr(config, "SPEED_MODE"):
                if config.SPEED_MODE == "low":
                    speed = config.SPEED_LOW
                elif config.SPEED_MODE == "medium":
                    speed = config.SPEED_MEDIUM
                elif config.SPEED_MODE == "high":
                    speed = config.SPEED_HIGH
                else:
                    raise ValueError(f"Unknown SPEED_MODE: {config.SPEED_MODE}")
            else:
                speed = 10  # fallback
            print(f"[Speed Sweep] Drone {i} speed set to {speed} m/s") #Sanity check
            # -------------------------------------------------------- #

            print('UAV: ', i, ' initial location is at: ', start_position[i], ' speed is: ', speed)
            drone = Drone(env=env,
                          node_id=i,
                          coords=start_position[i],
                          speed=speed,
                          inbox=self.channel.create_inbox_for_receiver(i),
                          simulator=self)

            self.drones.append(drone)

        # scatter_plot_with_spherical_obstacles(self)

        self.env.process(self.show_performance())
        self.env.process(self.show_time())

    def show_time(self):
        while True:
            print('At time: ', self.env.now / 1e6, ' s.')

            # the simulation process is displayed every 0.5s
            yield self.env.timeout(0.5*1e6)

    def show_performance(self):
        yield self.env.timeout(self.total_simulation_time - 1)

        scatter_plot(self)
        
        

        self.metrics.print_metrics()
        
    
#Metric accessors for visualizer    
###########################
    def get_route_path(self, src_id, dst_id):
        """
        Return the hop-by-hop route path from src → dst using AODV tables.
        """
        try:
            src_drone = self.drones[src_id]
            rt = src_drone.routing_protocol.route_table
            path = rt.get_path(dst_id)
            return path
        except Exception as e:
            print("Route lookup error:", e)
            return None

    def get_pdr(self):
        """
        Packet Delivery Ratio as a fraction in [0, 1].
        metrics.print_metrics() prints it as a percentage,
        but for plotting we keep it 0-1 so it matches the panel ylim.
        """
        if self.metrics.datapacket_generated_num == 0:
            return 0.0
        return len(self.metrics.datapacket_arrived) / self.metrics.datapacket_generated_num

    def get_avg_latency(self):
        """
        Average end-to-end latency in milliseconds.
        Values in deliver_time_dict are in microseconds.
        """
        if not self.metrics.deliver_time_dict:
            return 0.0
        return float(np.mean(list(self.metrics.deliver_time_dict.values())) / 1e3)

    def get_jitter(self):
        """
        Latency jitter = std dev of per-packet delay, in milliseconds.
        """
        if len(self.metrics.deliver_time_dict) <= 1:
            return 0.0
        delays_ms = np.array(list(self.metrics.deliver_time_dict.values())) / 1e3
        return float(np.std(delays_ms))

    def get_avg_queue_size(self):
        """
        Average size of the transmitting queues across all drones.
        This uses each drone's transmitting_queue.qsize() at the current time.
        """
        if not self.drones:
            return 0.0
        sizes = [d.transmitting_queue.qsize() for d in self.drones]
        return float(np.mean(sizes))

    def get_avg_energy(self):
        """
        Average remaining energy across all drones (Joules).
        If you later want 'energy used', you can normalize against INITIAL_ENERGY.
        """
        if not self.drones:
            return 0.0
        energies = [d.residual_energy for d in self.drones]
        return float(np.mean(energies))
    
############################


#Formation Change
############################
    def trigger_formation(self, mode):
        """Dispatcher that routes button clicks to the right formation."""
        if mode == "original":
            self.apply_original_formation()
        elif mode == "v":
            self.apply_v_formation()
        elif mode == "line":
            self.apply_line_formation()
        else:
            print("Unknown formation:", mode)

    def apply_original_formation(self):
        """Send all drones back to their original start positions."""
        for drone in self.drones:
            drone.set_target(drone.start_coords)
        print("\n--- Formation Set: ORIGINAL POSITIONS ---")
        
    def apply_v_formation(self):
        """Arrange drones into a V formation."""
        center_x = np.mean([d.coords[0] for d in self.drones])
        center_y = np.mean([d.coords[1] for d in self.drones])
        altitude = 50
        spacing = 25
        mid = len(self.drones) // 2
        
        for i, drone in enumerate(self.drones):
            offset = i - mid
            target = [
                center_x + abs(offset) * spacing,
                center_y + offset * spacing,
                altitude
            ]
            drone.set_target(target)
            
        print("\n--- Formation Set: V FORMATION ---")
        
    def apply_line_formation(self):
        """Arrange drones into a horizontal line."""
        n = len(self.drones)
        spacing = config.MAP_LENGTH / (n + 1)
        y = config.MAP_WIDTH / 2
        z = 50

        for i, drone in enumerate(self.drones):
            x = spacing * (i + 1)
            drone.set_target([x, y, z])

        print("\n--- Formation Set: LINE FORMATION ---")
############################
