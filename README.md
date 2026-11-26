# Green Mountain Grill for Home Assistant

Custom Home Assistant integration for Wi-Fi-enabled Green Mountain Grills (GMG) pellet smokers.

Forked from [`jwhitby91/gmg_home_assistant`](https://github.com/jwhitby91/gmg_home_assistant) and modernized with UI config flow, `DataUpdateCoordinator` polling, 16-bit temperature decoding, spike filtering, and full `sensor` / `binary_sensor` / `climate` entity support.

---

## Features

- **UI Config Flow & YAML Import**: Set up directly in the Home Assistant UI (via UDP broadcast discovery or static IP), with automatic import of legacy `climate: platform: gmg` YAML entries.
- **Single-Poll Coordinator**: Polls the grill once every **15 seconds** over UDP port `8080` and updates all entities together under a single GMG device.
- **16-Bit Temperature Decoding**: Properly decodes little-endian 16-bit temperatures above `255 °F` for both pit and probe readings.
- **Reliable Unplugged Probe Detection**: Detects GMG's out-of-range sentinel (such as `601 °F`, anything `> 257 °F`) so unplugged probes report `off` / `unknown` instead of bogus high temperatures.
- **Corrupted Packet & Spike Filtering**:
  - Rejects out-of-range/corrupted UDP status packets (`on` not in `0/1/2`, `temp > 650`, `grill_set_temp > 600`, or `probe*_set_temp > 257`).
  - Suppresses single-poll ADC/sensor spikes in `GmgDataUpdateCoordinator` by requiring **2 consecutive polls** before accepting large jumps (`> 35 °F` on the pit, `> 15 °F` on a connected probe).
- **Mode-Aware Probe Minimums**:
  - **Heat mode (`on == 1`)**: Probe `min_temp` is **`100 °F`** for cleaner thermostat control.
  - **Cold Smoke (`fan_only`) / Off**: Probe `min_temp` is **`32 °F`** so low ambient temperatures remain supported.
- **Temperature Steps & Bounds**:
  - **Grill Pit**: `150–500 °F` in **`5 °F`** steps (note: grill must be powered on and pit temp `>= 145 °F` before setting target temperature).
  - **Food Probes 1 & 2**: `32–257 °F` (`100–257 °F` in heat mode) in **`1 °F`** steps.

---

## Requirements

- **Network**: UDP port **`8080`** must be reachable between Home Assistant and your GMG grill.
- **Discovery vs. Static IP**:
  - Broadcast discovery (`UL!`) works when Home Assistant and the grill are on the same broadcast subnet.
  - Use a static `host` IP when running Home Assistant in Docker bridge mode, across VLANs, or if broadcast discovery is unreliable.

---

## Installation

### Option 1: Home Assistant Marketplace (Recommended)
1. Open **Settings → Marketplace** (or **Marketplace** in the Home Assistant sidebar).
2. Open the menu (top right) → **Custom repositories** and add `https://github.com/dpnguyen01/gmg_home_assistant` as **Integration**.
3. Search for **Green Mountain Grill**, install/download it, and **restart Home Assistant**.

### Option 2: Manual Installation
1. Copy `custom_components/gmg` into your Home Assistant `config/custom_components/gmg` directory.
2. **Restart Home Assistant**.

---

## Configuration

### UI Setup (Recommended)
1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Green Mountain Grill**.
3. Enter your grill's IP address (or leave blank to auto-discover via UDP broadcast).

### Legacy YAML (Auto-Imported)
If you previously configured the integration in `configuration.yaml`, it will be imported automatically into a UI config entry:

```yaml
climate:
  - platform: gmg
    host: 192.168.68.80 # optional; omit to use UDP broadcast auto-discovery
```

---

## Entities

All entities are grouped under a single device identified by the grill's serial number (for example, `GMG12148258`).

### Climate
| Entity | Description | Modes / Features | Range & Step |
| :--- | :--- | :--- | :--- |
| `<SERIAL>` | Grill Pit Control | `heat`, `fan_only` (Cold Smoke), `off`; `turn_on` / `turn_off` / `target_temperature` | `150–500 °F` (`5 °F` step) |
| `<SERIAL>_probe_1` | Meat Probe 1 | Reports `heat` when grill is on and probe is connected, otherwise `off`; `target_temperature` | `100–257 °F` in heat mode, `32–257 °F` in cold smoke/off (`1 °F` step) |
| `<SERIAL>_probe_2` | Meat Probe 2 | Reports `heat` when grill is on and probe is connected, otherwise `off`; `target_temperature` | `100–257 °F` in heat mode, `32–257 °F` in cold smoke/off (`1 °F` step) |

### Sensors
| Entity | Description | Values / Unit |
| :--- | :--- | :--- |
| `<SERIAL> Fire State` | Current fire controller state | `Off` (`0`), `Default` (`1`), `Startup` (`2`), `Running` (`3`), `Cool Down` (`4`), `Fail` (`5`) |
| `<SERIAL> Fire Percentage` | Auger / fan duty percentage | `%` (`measurement`) |
| `<SERIAL> Warning State` | Active grill warning text | `None` (`0`), `Fan Overloaded` (`1`), `Auger Overloaded` (`2`), `Ignitor Overloaded` (`3`), `Low Voltage` (`4`), `Low Pellets` (`5`) |
| `<SERIAL> Probe 1 Temperature` | Probe 1 current temperature | `°F` (`unknown`/`None` when unplugged) |
| `<SERIAL> Probe 2 Temperature` | Probe 2 current temperature | `°F` (`unknown`/`None` when unplugged) |

### Binary Sensors
| Entity | Device Class | Description |
| :--- | :--- | :--- |
| `<SERIAL> Probe 1 Connected` | `plug` | `on` when Probe 1 reading `<= 257 °F` |
| `<SERIAL> Probe 2 Connected` | `plug` | `on` when Probe 2 reading `<= 257 °F` |
| `<SERIAL> Warning` | `problem` | `on` when `warnState != 0` |

---

## GMG UDP Protocol Reference

Communication uses UDP port `8080`:

| Command | Payload | Purpose |
| :--- | :--- | :--- |
| Serial / Discovery | `UL!` | Returns grill serial number (`GMG...`) |
| Status Poll | `UR001!` | Returns 52+ byte binary status packet |
| Power On (Heat) | `UK001!` | Starts grill in heat mode (`on = 1`) |
| Cold Smoke | `UK002!` | Starts grill fan-only / cold smoke (`on = 2`) |
| Power Off | `UK004!` | Shuts down / cool-down mode (`on = 0`) |
| Set Pit Temp | `UT<temp>!` | Sets grill target temperature (`150–500 °F`) |
| Set Probe 1 Temp | `UF<temp>!` | Sets Probe 1 target temperature (`32–257 °F`) |
| Set Probe 2 Temp | `Uf<temp>!` | Sets Probe 2 target temperature (`32–257 °F`) |

---

## Development & Testing

Unit and regression tests stub out Home Assistant internals so they can run locally without a full Home Assistant installation:

```bash
python -m unittest tests/test_gmg.py -v
```

Current status: **11/11 tests passing** in `tests/test_gmg.py` (covering 16-bit decoding, unplugged probe detection, command bounds, corrupted packet rejection, coordinator single-poll spike filtering, cold smoke mode, and config flow).
