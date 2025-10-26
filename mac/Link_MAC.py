"""What must be implemented
 - Queue management
 - Neighbor table
 - CSMA/CA flow (sense -> backoff -> transmit)
 - ACK/retry
 - Beacons handling
 - Metrics
 """
import random
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple


class FrameType(Enum):
    DATA = 1
    ACK = 2
    BEACON = 3

class DroneRole(Enum):
    COMMAND_CONTROL = 1
    WORKER_DRONE = 2

@dataclass
class MACFrame:
    """MAC frame structure used in transmissions"""
    frame_type: FrameType
    source: str
    dest: Optional[str]              # NONE if sending a broadcast
    seq_num: int
    payload: bytes
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0

@dataclass
class Neighbor:
    node_id: str
    role: DroneRole
    last_seen: float
    signal_strength: float = 1.0
    position: Optional[Tuple[float, float, float]] = None

# ---------------------------------------------------------------------------------------------------------------------
# QUEUE MANAGEMENT
# ---------------------------------------------------------------------------------------------------------------------
class MACQueue:
    """
    FIFO queue with limited capacity.
    When the queue is full, it drops the oldest frame automatically.
    """

    def __init__(self, max_capacity: int = 100):
        """
        Initializes the queue.

        Args:
            max_capacity: Maximum number of frames the queue can hold.
        """
        self.transmissions_queue = deque(maxlen=max_capacity)
        self.max_capacity = max_capacity
        self.total_enqueued = 0
        self.total_dropped = 0

    def enqueue(self, frame: MACFrame) -> bool:
        """
        Add frame to the queue. If full, drop the oldest frame automatically.

        Returns:
            True if added without dropping.
            False if an old frame was dropped.
        """
        full = len(self.transmissions_queue) >= self.max_capacity

        self.transmissions_queue.append(frame)
        self.total_enqueued += 1

        if full:
            self.total_dropped += 1
            return False

        return True

    def dequeue(self) -> Optional[MACFrame]:
        """
        Remove and returns next frame.

        Returns:
            Frame if available, None is empty.
        """
        if len(self.transmissions_queue) == 0:
            return None

        return self.transmissions_queue.popleft()

    def size(self):
        return len(self.transmissions_queue)

    def is_empty(self) -> bool:
        return len(self.transmissions_queue) == 0

    def get_drop_count(self) -> int:
        return self.total_dropped


# ---------------------------------------------------------------------------------------------------------------------
# NEIGHBOR MANAGEMENT
# ---------------------------------------------------------------------------------------------------------------------
class NeighborTable:
    """
    C&C drone keeps track of all worker drones.
    Worker drone only tracks C&C drone.
    """
    def __init__(self, expiry_timeout: float = 10.0):
        """
        Initialized neighbor table.

        Args:
            expiry_timeout: Seconds before the neighbor is dropped from the table.
        """
        self.neighbor_table = {}
        self.expiry_timeout = expiry_timeout
        self.cnd_drone_id = None

    def add_or_update(self, node_id: str, role: DroneRole, signal_strength: float = 1.0,
                      position: Optional[Tuple[float, float, float]] = None):
        """
        Add new neighbor or update existing one.

        Args:
            node_id: Unique identifier
            role: C&C or WORKER
            signal_strength: default 1.0
            position: Current position of the drone
        """
        current_time = time.time()

        # Tracks if it is the C&C drone.
        if role == DroneRole.COMMAND_CONTROL:
            self.cnd_drone_id = node_id

        # Check if neighbor already exists in the table
        if node_id in self.neighbor_table:
            # Neighbor exist, update it
            neighbor = self.neighbor_table[node_id]
            neighbor.last_seen = current_time        # Update timestamp
            neighbor.signal_strength = signal_strength
            if position:
                neighbor.position = position
        else:
            # New neighbor, add it
            self.neighbor_table[node_id] = Neighbor(
                node_id = node_id,
                role = role,
                last_seen = current_time,
                signal_strength = signal_strength,
                position = position
            )

    def get_cnd_drone(self) -> Optional[Neighbor]:
        """
        Get the C&C drone information, will be used by workers to find their hub
        """
        if self.cnd_drone_id and self.cnd_drone_id in self.neighbor_table:
            return self.neighbor_table[self.cnd_drone_id]
        return None

    def get_active(self) -> List[Neighbor]:
        """
        Get all neighbors that have not expired.

        Returns:
            List of Neighbor objects that are still active.
        """
        current_time = time.time()
        active_neighbors = []

        for neighbor in self.neighbor_table.values():
            time_last_seen = current_time - neighbor.last_seen
            if time_last_seen < self.expiry_timeout:
                active_neighbors.append(neighbor)

        return active_neighbors

    def remove_expired(self) -> int:
        """
        Remove the expired neighbors from the list.

        Returns:
            Number of remove neighbors.
        """
        current_time = time.time()
        expired_neighbors = []

        for node_id, neighbor in self.neighbor_table.items():
            time_last_seen = current_time - neighbor.last_seen
            if time_last_seen >= self.expiry_timeout:
                expired_neighbors.append(node_id)

        for node_id in expired_neighbors:
            del self.neighbor_table[node_id]

        return len(expired_neighbors)

    def get_signal_strenght_to_cnd(self) -> float:
        """
        Get signal strength to C&C drone. Used by worker drones to decide if
        they need to move closer to the C&C before transmitting data.

        Returns:
            Signal strength to C&C (0.0-1.0)
            0.0 if C&C is not found
        """
        cnd = self.get_cnd_drone()              # Get C&C neighbor entry

        # if C&C is found, return its signal strength
        # Otherwise return 0.0 (no connection)
        return cnd.signal_strength if cnd else 0.0

# ---------------------------------------------------------------------------------------------------------------------
# CSMA/CA
# ---------------------------------------------------------------------------------------------------------------------
class CMSACA:
    """
    Implements the Carrier Sense Multiple Access with Collision Avoidance CMSA/CA protocol.
    """
    # -----------------------------------------------------------
    # Is the communication channel being implemented by another layer?????
    # -----------------------------------------------------------
    def __init__(self, channel: SharedChannel, min_backoff: float = 0.01, max_backoff: float = 0.1):
        """
        Initialize CSMA/CA controller

        Args:
            channel: Shared channel to transmit data on
            min_backoff: Minimum backoff time in seconds.
            max_backoff: Maximum backoff time in seconds.
        """
        self.channel = channel
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        self.current_backoff = min_backoff                  # Starts at minimum

    def transmit_with_csma(self, frame: MACFrame):
        """
        Attempt to transmit a frame using CSMA/CA

        Args:
            frame: The MAC Frame to be transmitted

        Returns:
            True - if the transmission was successful
            False - if the transmission was deferred (busy channel)
        """
        # Initial carrier sense - check if channel is busy
        if self.channel.is_busy():
            # Channel is busy, defer transmission and try again later
            return False

        # Calculate random backoff time to prevent multiple drones from transmitting simultaneously
        backoff_time = random.uniform(0, self.current_backoff)

        # Wait the backoff time, gives other drones an opportunity to access the channel
        # Spreads out transmissions to avoid collisions
        time.sleep(backoff_time)

        # Final carrier sense, double-check the channel is available
        if self.channel.is_busy():
            # Channel became busy during backoff, delay transmission
            return False

        # Channel is available, safe to transmit
        self.channel.transmit(frame)

        # Return success
        return True

    def increase_backoff(self):
        """
        Double the backoff window after collision or failure.

        Returns:
            Float with the new backoff time.
        """
        # Double current backoff, do not exceed the maximum
        self.current_backoff = min(self.current_backoff * 2, self.max_backoff)

    def reset_backoff(self):
        """
        Reset backoff window after a successful transmission.
        """
        self.current_backoff = self.min_backoff


# ---------------------------------------------------------------------------------------------------------------------
# ACK AND RETRY LOGIC
# ---------------------------------------------------------------------------------------------------------------------
class AckRetry:
    """
    Handles the ACKs and retransmissions.
    """

# ---------------------------------------------------------------------------------------------------------------------
# BEACON MANAGER
# ---------------------------------------------------------------------------------------------------------------------
class BeaconManager:
    """
    Send periodic broadcast beacons to announce presence to ground stations and other drones in the network.
    """

# ---------------------------------------------------------------------------------------------------------------------
# METRICS TRACKER
# ---------------------------------------------------------------------------------------------------------------------
class Metrics:
    """
    Keep track of performance matrics.
    """