# How to Customize WiFi Simulation Tech Profiles and Channels in UAVNetSim

## 1. Choose Which Tech Profile to Use

- In `main.py`, you select the tech profile with all radio/channel settings.

**Example:**
```python
selected_profile = wifi_11ac   # Change to wifi_11n or wifi_direct to switch!
sim.channel = create_channel(env, selected_profile)
print(f"Using tech profile: {selected_profile.name}")
```

## 2. Set Loss Probability (Packet Loss Rate)

- In your profile definition (`wifi_11n`, `wifi_11ac`, `wifi_direct`, etc.):

**Example:**
```python
wifi_11ac = WifiProfile(
    ...,
    channel_class = ProbChannel,
    channel_params = {"loss_prob": 0.15}     # <-- Set desired loss rate
)
```
- To change packet loss, adjust `"loss_prob": VALUE` as needed.

## 3. Use a Different Channel (Broadcast Type)

- To use a different broadcast or channel model (e.g., distance-based), create a new channel class and set it in your profile:

**Example:**
```python
my_custom_channel = MyCustomChannel
wifi_custom = WifiProfile(
    ...,
    channel_class = my_custom_channel,
    channel_params = {"some_custom_param": value}
)
```
- Then, select this profile in your main script.

## 4. Add or Modify Profiles

- You can copy existing profiles and make new ones with different parameters, names, MCS tables, etc.

**Example:**
```python
wifi_superfast = WifiProfile(
    name="SuperFast Wi-Fi",
    mcs_table={ ... },
    ...
    channel_class = ProbChannel,
    channel_params = {"loss_prob": 0.05}
)
```

## 5. Common Params to Customize

- `loss_prob`: Set packet loss probability (`0.0` = never drop, `1.0` = always drop).
- `channel_class`: Choose which channel/broadcast implementation to use.
- `channel_params`: Pass custom logic/thresholds for your channel logic.
- Other profile fields: change MCS tables, channel widths, etc., for scenario realism.

## 6. How Broadcast Logic is Used

- The type of broadcast depends on which channel class you use (`ProbChannel`, `RangeChannel`, etc.).
- You control delivery/loss logic in your channel implementation (override `broadcast_put` if you like!).
- The simulation sends packets by calling:  
  ```python
  sim.channel.broadcast_put(packet)
  ```

---

## TL;DR Cheat Sheet

- **Change profile:** Update `selected_profile = wifi_11ac` in main.
- **Change packet loss:** Set `"loss_prob": VALUE` in profile.
- **Change broadcast model:** Set/implement `channel_class` in profile.
- **Print correct profile:** Use `selected_profile.name`.

---

## Example Complete Main.py Setup

```python
# Select and use desired tech profile/channel
selected_profile = wifi_11ac
sim.channel = create_channel(env, selected_profile)
print(f"Using tech profile: {selected_profile.name}")
print(f"Channel loss probability: {sim.channel.loss_prob}")
```

---

## Tips

- Always use a variable for your tech profile (`selected_profile`) in main, never hardcode profile names in print statements!
- You can add unlimited custom profiles for experiments.
- Document reasons for your choices for future clarity.

