import random
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple, Dict, Callable


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

    def get_signal_strength_to_cnd(self) -> float:
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
class CSMACA:
    """
    Implements the Carrier Sense Multiple Access with Collision Avoidance CSMA/CA protocol.
    """
    def __init__(self, channel, my_drone, min_backoff: float = 0.01, max_backoff: float = 0.1):
        """
        Initialize CSMA/CA controller

        Args:
            channel:ProbChannel object from prob_channel.py
            my_drone: Reference to drone object
            min_backoff: Minimum backoff time in seconds.
            max_backoff: Maximum backoff time in seconds.
        """
        self.channel = channel
        self.my_drone = my_drone
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        self.current_backoff = min_backoff                  # Starts at minimum

    def transmit_with_csma(self, frame: MACFrame) -> bool:
        """
        Attempt to transmit a frame using CSMA/CA

        Args:
            frame: The MAC Frame to be transmitted

        Returns:
            True - if the transmission was successful
            False - if the transmission was deferred (busy channel)
        """
        # Initial carrier sense - check if channel is busy
        if self._is_channel_busy():
            # Channel is busy, defer transmission and try again later
            return False

        # Calculate random backoff time to prevent multiple drones from transmitting simultaneously
        backoff_time = random.uniform(0, self.current_backoff)

        # Wait the backoff time, gives other drones an opportunity to access the channel
        # Spreads out transmissions to avoid collisions
        time.sleep(backoff_time)

        # Final carrier sense, double-check the channel is available
        if self._is_channel_busy():
            # Channel became busy during backoff, delay transmission
            return False

        # Channel is available, safe to transmit
        if frame.dest is None:
            # Broadcast to beacons
            self.channel.broadcast_put(frame)

        else:
            # Unicast (data, ACK)
            self.channel.unicast_put(frame, frame.dest)

        # Return success
        return True

    def _is_channel_busy(self) -> bool:
        """
        Check if channel is busy (carrier sensing)
        """
        # Simplified carrier sense for simulation
        # For now always return true (channel is available)
        # Random backoff provides collision avoidance.
        return False

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
    def __init__(self, mac_queue: MACQueue, csma_controller: CSMACA, channel, my_drone, max_retries: int = 3, ack_timeout: float = 0.05):
        """
        Initializes ACK/Retry handler.

        Args:
            mac_queue: The queue to put frames back into for retransmission.
            csma_controller: The CSMA/CA controller for backoff management.
            channel: PropChannel from prob_channel.py.
            my_drone: Reference to drone object.
            max_retries: Maximum number of times to retry a frame.
            ack_timeout: Time to wait for an ACK before considering it a failure.
        """
        self.mac_queue = mac_queue
        self.csma_controller = csma_controller
        self.channel = channel
        self.my_drone = my_drone
        self.max_retries = max_retries
        self.ack_timeout = ack_timeout
        # Stores frames waiting for an ACK: { (dest, seq_num): MACFrame }
        self.pending_acks: Dict[Tuple[str, int], MACFrame] = {}

    def is_awaiting_ack(self, frame: MACFrame) -> bool:
        """Check if an ACK is expected for a given frame."""
        if not frame.dest:
            return False # Broadcasts don't need ACKs in this simple model
        return (frame.dest, frame.seq_num) in self.pending_acks

    def register_sent_frame(self, frame: MACFrame):
        """Register a frame as sent and awaiting ACK."""
        if frame.dest: # Only track frames sent to a specific destination
            self.pending_acks[(frame.dest, frame.seq_num)] = frame

    def process_ack(self, ack_frame: MACFrame) -> bool:
        """
        Process a received ACK frame.

        Args:
            ack_frame: The MACFrame containing the ACK.

        Returns:
            True if the ACK matched a pending frame and was successfully processed.
        """
        if ack_frame.frame_type != FrameType.ACK:
            return False

        # The ACK is for a frame *sent* by the ACK receiver, so the ACK's source is the original frame's destination
        key = (ack_frame.source, ack_frame.seq_num) 
        
        if key in self.pending_acks:
            del self.pending_acks[key]
            self.csma_controller.reset_backoff() # Successful transmission, reset backoff
            # print(f"[ACK] Received ACK from {ack_frame.source} for seq {ack_frame.seq_num}. Transmission complete.")
            return True
        # print(f"[ACK] Received stray ACK from {ack_frame.source} for seq {ack_frame.seq_num}. (Not pending)")
        return False

    def check_timeouts_and_retry(self):
        """
        Check for pending ACKs that have timed out and handle retransmission/dropping.
        """
        current_time = time.time()
        frames_to_retry: List[MACFrame] = []
        keys_to_remove: List[Tuple[str, int]] = []

        for key, frame in self.pending_acks.items():
            if current_time - frame.timestamp > self.ack_timeout:
                keys_to_remove.append(key)
                
                if frame.retry_count < self.max_retries:
                    frame.retry_count += 1
                    frame.timestamp = time.time() # Update timestamp for next timeout check
                    frames_to_retry.append(frame)
                    self.csma_controller.increase_backoff() # Increase backoff on failed attempt
                    # print(f"[RETRY] ACK timeout for {key}. Retrying (Attempt {frame.retry_count}).")
                else:
                    # print(f"[DROP] Frame {key} dropped after {self.max_retries} retries.")
                    # In a real system, you would update metrics for dropped frames here
                    pass

        # Remove timed-out frames from pending list
        for key in keys_to_remove:
            if key in self.pending_acks:
                del self.pending_acks[key]

        # Enqueue frames for retry
        for frame in frames_to_retry:
            self.mac_queue.enqueue(frame)

    def create_ack_frame(self, original_frame: MACFrame, node_id: str) -> MACFrame:
        """
        Create an ACK frame in response to a received data frame.
        
        Args:
            original_frame: The frame being acknowledged.
            node_id: The ID of the drone creating the ACK.
        """
        return MACFrame(
            frame_type=FrameType.ACK,
            source=node_id,
            dest=original_frame.source,
            seq_num=original_frame.seq_num,
            payload=b'' # ACK frames typically have no payload
        )

# ---------------------------------------------------------------------------------------------------------------------
# BEACON MANAGER
# ---------------------------------------------------------------------------------------------------------------------
class BeaconManager:
    """
    Send periodic broadcast beacons to announce presence to ground stations and other drones in the network.
    """
    def __init__(self, node_id: str, role: DroneRole, channel, beacon_interval: float = 1.0,
                 get_position_func: Callable[[], Optional[Tuple[float, float, float]]] = lambda: None):
        """
        Initialize Beacon Manager.

        Args:
            node_id: Unique identifier of the drone.
            role: The role of the drone (C&C or WORKER).
            channel: PropChannel from prob_channel.py.
            beacon_interval: Time in seconds between beacon transmissions.
            get_position_func: A function to call to get the drone's current position.
        """
        self.node_id = node_id
        self.role = role
        self.channel = channel
        self.beacon_interval = beacon_interval
        self.last_beacon_time = 0.0
        self.seq_num_counter = 0
        self.get_position = get_position_func

    def send_beacon(self):
        """
        Send beacon using ProbChannel.broadcast_put().
        """
        beacon_frame = self.create_beacon_frame()
        # Broadcast using channel.py
        self.channel.broadcast_put(beacon_frame)

    def needs_to_send_beacon(self) -> bool:
        """Check if it's time to send a new beacon."""
        return (time.time() - self.last_beacon_time) >= self.beacon_interval

    def create_beacon_frame(self) -> MACFrame:
        """
        Create a MACFrame for a beacon. The payload contains the drone's role and position.
        """
        self.seq_num_counter += 1
        self.last_beacon_time = time.time()
        
        # Payload format: (role_value, position_tuple_or_None)
        position = self.get_position()
        payload = f"{self.role.value},{position or ''}".encode('utf-8')

        return MACFrame(
            frame_type=FrameType.BEACON,
            source=self.node_id,
            dest=None, # Broadcast frame
            seq_num=self.seq_num_counter,
            payload=payload
        )

    @staticmethod
    def parse_beacon_payload(payload: bytes) -> Optional[Tuple[DroneRole, Optional[Tuple[float, float, float]]]]:
        """
        Parse the role and position from a beacon frame's payload.
        
        Returns:
            A tuple of (DroneRole, Optional[PositionTuple]) or None on failure.
        """
        try:
            parts = payload.decode('utf-8').split(',')
            if not parts or len(parts) < 1:
                return None
            
            role_value = int(parts[0])
            role = DroneRole(role_value)
            
            position = None
            if len(parts) >= 2 and parts[1]:
                # Assuming position is encoded as comma-separated floats if available
                pos_parts = parts[1].strip('() ').split(' ') # Simple split based on common tuple string
                if len(pos_parts) == 3:
                    position = (float(pos_parts[0]), float(pos_parts[1]), float(pos_parts[2]))
            
            return role, position
        except Exception as e:
            # print(f"Error parsing beacon payload: {e}")
            return

# ---------------------------------------------------------------------------------------------------------------------
# MAIN MAC LAYER - INTEGRATES WITH CHANNEL.PY
# ---------------------------------------------------------------------------------------------------------------------
class MACLayer:
    """
    Main MAC Layer that integrates with prob_channel.py
    Primary interface for the drone to use the MAC layer services.
    """
    def __init__(self, my_drone, role: DroneRole, cnd_id: Optional[str] = None, queue_capacity: int = 50):
        """
        Initialize MAC Layer for the drone.

        Args:
            my_drone: The drone object.
            role: COMMAND_CONTROL or WORKER_DRONE.
            cnd_id: C&C drone ID.
            queue capacity: Maximum queue size.
        """
        # Store references
        self.my_drone = my_drone
        self.node_id = my_drone.identifier
        self.role = role
        self.cnd_id = cnd_id

        # Get channel simulator
        self.channel = my_drone.simulator.channel
        self.env = my_drone.env

        # Initialize MAC queue
        self.queue = MACQueue(max_capacity=queue_capacity)

        # Initialize CSMA/CA with ProbChannel
        self.csma = CSMACA(
            channel=self.channel,
            my_drone=my_drone,
            min_backoff=0.01,
            max_backoff=0.1
        )

        # Initialize ACK/Retry with ProbChannel
        self.ack_retry = AckRetry(
            mac_queue=self.queue,
            csma_controller=self.csma,
            channel=self.channel,
            my_drone=my_drone,
            max_retries=3,
            ack_timeout=0.05
        )

        # Initialize Beacon Manager with ProbChannel
        self.beacon_manager = BeaconManager(
            node_id=self.node_id,
            role=self.role,
            channel=self.channel,
            beacon_interval=1.0,
            get_position_func=lambda: getattr(my_drone, 'coords', None)
        )

        # Initialize Neighbor Table
        self.neighbor_table = NeighborTable(expiry_timeout=10.0)

        # Initialize Metrics
        self.metrics = Metrics(node_id=self.node_id)

        # State
        self.sequence_num = 0
        self.received_data_frames = deque()

        # Validation
        if role == DroneRole.WORKER_DRONE and cnd_id is None:
            raise ValueError("Worker drones must specified cnd_id")

    def send(self, payload: bytes) -> bool:
        """
        Send data (called by Network Layer or GUI).
    
        This is the MAC layer's SERVICE INTERFACE for upper layers.
        Network Layer (or GUI for testing) calls this to transmit data.
    
        Args:
            payload: Data bytes to send (comes from Network Layer)
                - For workers: Network Layer provides routing info + data
                - For C&C: Network Layer provides aggregated data
            
        Returns:
            True if queued successfully, False if queue full
        """
        # Determine destination depending on role
        if self.role == DroneRole.WORKER_DRONE:
            dest = self.cnd_id      # Worker sends to C&C
        else:
            dest = None     # C&C broadcast

        # Create Data frame
        frame = MACFrame(
            frame_type=FrameType.DATA,
            source=self.node_id,
            dest=dest,
            seq_num=self.sequence_num,
            payload=payload
        )
        self.sequence_num += 1

        # Enqueue
        success = self.queue.enqueue(frame)
        if not success:
            self.metrics.mac_queue_drops += 1

        return success

    def receive(self) -> Optional[Tuple[str, bytes]]:
        """
        Receive data (called by Network Layer or GUI).

        This is the MAC layer's SERVICE INTERFACE for upper layers.
        Network Layer (or GUI for testing) calls this to retrieve received data.

        Returns:
            (source_id, payload) tuple if data available, None otherwise
                - source_id: Which drone sent this
                - payload: The data bytes (Network Layer will parse this)
        """
        if len(self.received_data_frames) == 0:
            return None

        frame = self.received_data_frames.popleft()
        return frame.source, frame.payload

    def process_outgoing(self):
        """
        Process outgoing queue, transmit waiting frames

        Call this repeatedly in main even loop to send queue frames
        """

        # Check for ACK timeouts and handle retries
        if not self.queue.is_empty():
            frame = self.queue.dequeue()
            if frame:
                self.metrics.record_tx_attempt()

                # Try CSMA/CA transmission
                # This calls ProbChannel.unicast_put() or ProbChannel.broadcast_put()
                success = self.csma.transmit_with_csma(frame)

                if success:
                    self.metrics.record_transmission(frame.frame_type)

                    # If DATA frame to specific dest, register for ACK
                    if frame.frame_type == FrameType.DATA and frame.dest:
                        self.ack_retry.register_sent_frame(frame)
                else:
                    # Channel is busy, retry
                    self.queue.enqueue(frame)
                    self.metrics.record_csma_deferral()

    def send_beacon_if_needed(self):
        """
        Sends beacon if it's time.
        Call this periodically in main.
        """
        if self.beacon_manager.needs_to_send_beacon():
            self.beacon_manager.send_beacon()
            self.metrics.record_transmission(FrameType.BEACON)

    def cleanup_neighbors(self):
        """
        Remove expired neighbors from table
        Call this periodically (every 5-10 seconds)

        Returns:
            Number of neighbors removed
        """
        return self.neighbor_table.remove_expired()

    def get_metrics(self) -> Dict:
        """
        Get performance metrics

        Returns:
            Dictionary with MAC Layer performance stats
        """
        self.metrics.update_queue_drops(self.queue)
        return self.metrics.get_summary()

    def get_neighbors(self) -> List[Neighbor]:
        """
        Get list of active neighbors

        Returns:
            List of Neighbor objects that have not expired
        """
        return self.neighbor_table.get_active()

    def should_move_closer_to_cnd(self) -> bool:
        """
        Check if worker drone should move closer to C&C for better signal

        Only applies to WORKER_DRONE role.

        Returns:
            True if it should move closer, False otherwise
        """

        if self.role != DroneRole.WORKER_DRONE:
            return False

        # Get signal strength to C&C
        signal = self.neighbor_table.get_signal_strength_to_cnd()

        # If weak signal and have data to send, move closer
        WEAK_SIGNAL_THRESHOLD = 0.3

        if signal < WEAK_SIGNAL_THRESHOLD and not self.queue.is_empty():
            return True

        return False

# ---------------------------------------------------------------------------------------------------------------------
# METRICS TRACKER
# ---------------------------------------------------------------------------------------------------------------------
class Metrics:
    """
    Keep track of performance matrics.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.start_time = time.time()
        
        # Transmission/Reception Counts
        self.tx_data_frames = 0
        self.rx_data_frames = 0
        self.tx_ack_frames = 0
        self.rx_ack_frames = 0
        self.tx_beacon_frames = 0
        self.rx_beacon_frames = 0
        
        # CSMA/CA and Retry Performance
        self.tx_attempts = 0            # Total transmission attempts (before successful CSMA/CA)
        self.csma_deferrals = 0         # Count of times channel was busy (CSMA sense failed)
        self.tx_successes = 0           # Frames successfully transmitted (ACK received)
        self.tx_failures = 0            # Frames dropped after max retries
        self.total_retries = 0          # Total number of retransmissions
        self.mac_queue_drops = 0        # Frames dropped due to full MAC queue (from MACQueue)

    def record_tx_attempt(self):
        """Record a single attempt to transmit a frame via CSMA/CA."""
        self.tx_attempts += 1
        
    def record_csma_deferral(self):
        """Record a deferred transmission due to a busy channel."""
        self.csma_deferrals += 1

    def record_transmission(self, frame_type: FrameType):
        """Record a frame successfully sent out onto the channel (CSMA/CA success)."""
        if frame_type == FrameType.DATA:
            self.tx_data_frames += 1
        elif frame_type == FrameType.ACK:
            self.tx_ack_frames += 1
        elif frame_type == FrameType.BEACON:
            self.tx_beacon_frames += 1
            
    def record_reception(self, frame_type: FrameType):
        """Record a frame successfully received from the channel."""
        if frame_type == FrameType.DATA:
            self.rx_data_frames += 1
        elif frame_type == FrameType.ACK:
            self.rx_ack_frames += 1
        elif frame_type == FrameType.BEACON:
            self.rx_beacon_frames += 1

    def record_tx_success(self):
        """Record a frame successfully completed (ACK received)."""
        self.tx_successes += 1

    def record_tx_failure(self, retries: int):
        """Record a frame dropped after reaching max retries."""
        self.tx_failures += 1
        self.total_retries += retries

    def update_queue_drops(self, queue: MACQueue):
        """Update the queue drop count from the MACQueue."""
        self.mac_queue_drops = queue.get_drop_count()

    def get_summary(self) -> Dict:
        """Generate a summary of all metrics."""
        duration = time.time() - self.start_time
        
        # Calculate derived metrics
        data_tx_rate = self.tx_data_frames / duration if duration > 0 else 0
        total_tx_frames = self.tx_data_frames + self.tx_ack_frames + self.tx_beacon_frames
        total_rx_frames = self.rx_data_frames + self.rx_ack_frames + self.rx_beacon_frames
        tx_efficiency = (self.tx_successes / self.tx_attempts) * 100 if self.tx_attempts > 0 else 0

        return {
            "node_id": self.node_id,
            "runtime_sec": round(duration, 2),
            "--- Total Frames ---": "",
            "total_tx_frames": total_tx_frames,
            "total_rx_frames": total_rx_frames,
            "data_tx_frames": self.tx_data_frames,
            "data_rx_frames": self.rx_data_frames,
            "--- Queue/CSMA Metrics ---": "",
            "tx_attempts": self.tx_attempts,
            "tx_successes": self.tx_successes,
            "tx_failures_max_retry": self.tx_failures,
            "total_retries": self.total_retries,
            "csma_deferrals": self.csma_deferrals,
            "mac_queue_drops": self.mac_queue_drops,
            "--- Derived Performance ---": "",
            "data_tx_rate_per_sec": round(data_tx_rate, 2),
            "tx_efficiency_percent": round(tx_efficiency, 2)
        }
    