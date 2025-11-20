from .prob_channel import ProbChannel

class WifiProfile:
    def __init__(
        self,
        name,
        mcs_table,
        channel_widths,
        tx_power_range,
        rate_adaptation,
        mesh_support,
        energy_model,
        frequency_bands,
        spatial_streams,
        guard_intervals,
        max_packet_size,
        channel_class=None,
        channel_params=None,
    ):
        self.name = name
        self.mcs_table = mcs_table
        self.channel_widths = channel_widths
        self.tx_power_range = tx_power_range
        self.rate_adaptation = rate_adaptation
        self.mesh_support = mesh_support
        self.energy_model = energy_model
        self.frequency_bands = frequency_bands
        self.spatial_streams = spatial_streams
        self.guard_intervals = guard_intervals
        self.max_packet_size = max_packet_size

        # now included prob_channels
        self.channel_class = channel_class
        self.channel_params = channel_params


wifi_11n = WifiProfile(
    name="802.11n",
    mcs_table = {2:0, 5:1, 9:2, 12:3, 15:4, 18:5, 21:6, 25:7},  # Correct mapping
    channel_widths=[20, 40],                 # MHz
    tx_power_range=(1, 20),                  # dBm
    rate_adaptation="minstrel",
    mesh_support=False,
    energy_model={"TX": 1000, "RX": 800, "Idle": 100, "Sleep": 5},  # mW (test values future implementation)
    frequency_bands=["2.4GHz", "5GHz"],
    spatial_streams=2,
    guard_intervals=[400, 800],               # ns
    max_packet_size=7935,                      # bytes
    channel_class = ProbChannel,
    channel_params = {"loss_prob": 0.15}
)

wifi_11ac = WifiProfile(
    name="802.11ac",
    # SNR → VHT MCS index (test values; expand/refine later)
    mcs_table = {2:0, 5:1, 9:2, 12:3, 15:4, 18:5, 21:6, 25:7, 30:8, 33:9},
    channel_widths=[20, 40, 80, 160],       # MHz
    tx_power_range=(1, 23),                 # dBm
    rate_adaptation="minstrel_ht",          # minstrel variant commonly used for HT/VHT
    mesh_support=False,
    energy_model={"TX": 1200, "RX": 900, "Idle": 120, "Sleep": 5},  # mW (test values)
    frequency_bands=["5GHz"],               # 11ac is primarily 5 GHz
    spatial_streams=4,                      # typical upper common config; spec allows up to 8
    guard_intervals=[400, 800],             # ns (Short/Long GI)
    max_packet_size=11454,                   # bytes (typical max A-MSDU/MPDU size for 11ac)
    channel_class = ProbChannel,
    channel_params = {"loss_prob": 0.15}
)

wifi_direct = WifiProfile(
    name="Wi-Fi Direct (P2P)",
    # SNR → MCS index (test values; depends on underlying PHY, often 11n)
    mcs_table = {2:0, 5:1, 9:2, 12:3, 15:4, 18:5, 21:6, 25:7},
    channel_widths=[20, 40],                # MHz (common for P2P)
    tx_power_range=(1, 20),                 # dBm (device/region dependent)
    rate_adaptation="minstrel",             # typical for 11n-based stacks
    mesh_support=False,                     # P2P is group-owner/client, not mesh
    energy_model={"TX": 900, "RX": 700, "Idle": 100, "Sleep": 5},   # mW (test values)
    frequency_bands=["2.4GHz", "5GHz"],     # depends on device capability
    spatial_streams=2,                      # many P2P devices use 1–2 streams
    guard_intervals=[400, 800],             # ns
    max_packet_size=7935,                    # bytes (11n-style A-MSDU limit common in P2P)
    channel_class = ProbChannel,
    channel_params = {"loss_prob": 0.15}
)

