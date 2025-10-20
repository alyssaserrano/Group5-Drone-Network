"""What must be implemented
 - Queue management
 - Neighbor table
 - CSMA/CA flow (sense -> backoff -> transmit
 - ACK/retry
 - Beacons handling
 - Metrics
 """
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class FrameType(Enum):
    DATA = 1
    ACK = 2
    BEACON = 3

class NodeType(Enum):
    DRONE = 1
    GROUND_SENSOR = 2

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
    node_type: NodeType
    last_seen: float
    signal_strength: float = 1.0

# ---------------------------------------------------------------------------------------------------------------------
# QUEUE MANAGEMENT
# ---------------------------------------------------------------------------------------------------------------------
class MACQueue:
    """
    Simple FIFO queue with capacity limit.
    When the queue is full drops the oldest frame automatically.
    """

    def __init__(self, max_capacity: int = 100):
        """
        Initializes the queue.

        Args:
            max_capacity: Maximun number of frames the queue can hold.
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
    Keep track of nearby nodes using beacons.
    """
    def __init__(self, expiry_timeout: float = 10.0):
        """
        Initialized neighbor table.

        Args:
            expiry_timeout: Seconds before the neighbor is dropped from the table.
        """
        self.neighbor_table = {}
        self.expiry_timeout = expiry_timeout

    def add_or_update(self, node_id: str, node_type: NodeType, signal_strength: float = 1.0):
        """
        Add new neighbor or update existing one.

        Args:
            node_id: Unique identifier
            node_type: DRONE or GROUND_SENSOR
            signal_strength: default 1.0
        """
        current_time = time.time()

        # Check if neighbor already exists in the table
        if node_id in self.neighbor_table:
            # Neighbor exist, update it
            neighbor = self.neighbor_table[node_id]
            neighbor.last_seen = current_time        # Update timestamp
            neighbor.signal_strength = signal_strength
        else:
            # New neighbor, add it
            new_neighbor = Neighbor(
                node_id = node_id,
                node_type = node_type,
                last_seen = time.time(),
                signal_strength = signal_strength
            )
            self.neighbor_table[node_id] = new_neighbor

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

# ---------------------------------------------------------------------------------------------------------------------
# CSMA/CA
# ---------------------------------------------------------------------------------------------------------------------
class CMSACA:
    """
    Implements the Carrier Sense Multiple Access with Collision Avoidance CMSA/CA protocol.
    """

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