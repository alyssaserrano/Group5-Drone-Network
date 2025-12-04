import random
from utils import config
from utils.util_function import euclidean_distance_3d


class LeaderFollower3D:
    """
    Simple 3D Leader–Follower / Formation mobility model.

    - Drone with identifier 0 is the leader
    - All other drones are followers
    - Followers try to stay at a fixed offset around the leader
    - At config.FORMATION_SWITCH_TIME the offsets change -> formation/topology switch
    """

    def __init__(self, drone):
        self.model_identifier = "LeaderFollower3D"
        self.my_drone = drone
        self.env = drone.simulator.env

        # DEBUG: show that LeaderFollower3D is being used
        print(f"[LeaderFollower3D] Drone {drone.identifier} initialized. "
              f"Switch at {config.FORMATION_SWITCH_TIME/1e6:.1f}s")

        # time step for position updates (microseconds)
        self.position_update_interval = 1 * 1e5  # 0.1 s

        # leader id (drone 0)
        self.leader_id = 0

        # map boundaries
        self.min_x = 0.0
        self.max_x = float(config.MAP_LENGTH)
        self.min_y = 0.0
        self.max_y = float(config.MAP_WIDTH)
        self.min_z = 0.0
        self.max_z = float(config.MAP_HEIGHT)

        # random generator for leader waypoints
        self.rng = random.Random(self.my_drone.identifier + self.my_drone.simulator.seed + 123)

        # offsets BEFORE the switch (star / cluster around leader)
        self.initial_offsets = {
            1: (50.0, 0.0, 0.0),
            2: (-50.0, 0.0, 0.0),
            3: (0.0, 50.0, 0.0),
            # add more if NUMBER_OF_DRONES > 4
        }

        # offsets AFTER the switch (line behind leader -> new formation)
        self.switched_offsets = {
            1: (30.0, -60.0, 0.0),
            2: (0.0, -120.0, 0.0),
            3: (-30.0, -180.0, 0.0),
        }

        self.switched = False

        # current target waypoint for leader
        self.leader_target = None

        # start the mobility process
        self.env.process(self.mobility_update(self.my_drone))

    # ------------- helpers ------------- #

    def _random_waypoint_in_map(self):
        """Pick a random point inside the 3D map for the leader."""
        x = self.rng.uniform(self.min_x + 20.0, self.max_x - 20.0)
        y = self.rng.uniform(self.min_y + 20.0, self.max_y - 20.0)
        z = self.rng.uniform(self.min_z + 10.0, self.max_z - 10.0)
        return [x, y, z]

    def _step_towards(self, current_pos, target_pos, speed):
        """Return (new_position, velocity_vector)."""
        dist = euclidean_distance_3d(current_pos, target_pos)
        if dist <= 1e-6:
            return current_pos[:], [0.0, 0.0, 0.0]

        dt = self.position_update_interval / 1e6  # seconds
        step = speed * dt

        if step >= dist:
            new_pos = target_pos[:]
        else:
            ratio = step / dist
            new_pos = [
                current_pos[0] + (target_pos[0] - current_pos[0]) * ratio,
                current_pos[1] + (target_pos[1] - current_pos[1]) * ratio,
                current_pos[2] + (target_pos[2] - current_pos[2]) * ratio,
            ]

        vx = (new_pos[0] - current_pos[0]) / dt
        vy = (new_pos[1] - current_pos[1]) / dt
        vz = (new_pos[2] - current_pos[2]) / dt

        return new_pos, [vx, vy, vz]

    def _clamp_to_map(self, pos):
        pos[0] = min(max(pos[0], self.min_x), self.max_x)
        pos[1] = min(max(pos[1], self.min_y), self.max_y)
        pos[2] = min(max(pos[2], self.min_z), self.max_z)
        return pos

    # ------------- main mobility loop ------------- #

    def mobility_update(self, drone):
        """
        Main SimPy loop. Called once per drone that installs this model.
        """
        while True:
            now = self.env.now

            # check if we have passed the formation switch time
            if (not self.switched) and now >= config.FORMATION_SWITCH_TIME:
                self.switched = True
                if drone.identifier == self.leader_id:
                    print(f"[LeaderFollower3D] Formation switched at t={now/1e6:.1f}s")

            if drone.identifier == self.leader_id:
                # ---------- LEADER ----------
                if self.leader_target is None:
                    self.leader_target = self._random_waypoint_in_map()

                cur_pos = drone.coords
                speed = drone.speed  # m/s

                next_pos, vel = self._step_towards(cur_pos, self.leader_target, speed)

                # if close enough to target, pick a new waypoint
                if euclidean_distance_3d(next_pos, self.leader_target) < 5.0:
                    self.leader_target = self._random_waypoint_in_map()

                next_pos = self._clamp_to_map(next_pos)

                drone.coords = next_pos
                drone.velocity = vel

            else:
                # ---------- FOLLOWERS ----------
                leader = drone.simulator.drones[self.leader_id]
                leader_pos = leader.coords

                # choose which offset table to use
                if not self.switched:
                    offset = self.initial_offsets.get(drone.identifier, (0.0, 0.0, 0.0))
                else:
                    offset = self.switched_offsets.get(drone.identifier, (0.0, 0.0, 0.0))

                target = [
                    leader_pos[0] + offset[0],
                    leader_pos[1] + offset[1],
                    leader_pos[2] + offset[2],
                ]

                cur_pos = drone.coords
                speed = drone.speed

                next_pos, vel = self._step_towards(cur_pos, target, speed)
                next_pos = self._clamp_to_map(next_pos)

                drone.coords = next_pos
                drone.velocity = vel

            # energy consumption similar to other mobility models
            energy_consumption = (
                self.position_update_interval / 1e6
            ) * drone.energy_model.power_consumption(drone.speed)
            drone.residual_energy -= energy_consumption

            # wait until next mobility step
            yield self.env.timeout(self.position_update_interval)