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


wifi_11n = WifiProfile(
    name="802.11n",
    mcs_table={10: 0, 15: 1, 20: 2, 25: 3},  # SNR→MCS index mapping (test values future implementation)
    channel_widths=[20, 40],                 # MHz
    tx_power_range=(1, 20),                  # dBm
    rate_adaptation="minstrel",
    mesh_support=False,
    energy_model={"TX": 1000, "RX": 800, "Idle": 100, "Sleep": 5},  # mW (test values future implementation)
    frequency_bands=["2.4GHz", "5GHz"],
    spatial_streams=2,
    guard_intervals=[400, 800],               # ns
    max_packet_size=7935                      # bytes
)

# wifi_11ac = WifiProfile(...)
# wifi_direct = WifiProfile(...)
