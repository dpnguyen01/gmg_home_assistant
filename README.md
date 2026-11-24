# Green Mountain Grill for Home Assistant

Fork of `jwhitby91/gmg_home_assistant` with 16-bit temperature decoding (`>255 °F` and unplugged probe detection), shared `DataUpdateCoordinator` polling, optional static `host` support, and `sensor` / `binary_sensor` entities.

## Installation

Install via HACS:
1. Open **HACS** → 3 dots in top right → **Custom repositories**
2. Add `https://github.com/dpnguyen01/gmg_home_assistant` as category **Integration**
3. Search & install **Green Mountain Grill**
4. Add to `configuration.yaml` and restart Home Assistant:

```yaml
climate:
  - platform: gmg
    host: 192.168.68.80 # optional; omit to use UDP broadcast auto-discovery
```

## Requirements
- UDP port `8080` reachable between Home Assistant & GMG
- Auto-discovery (`grills()`) finds GMG devices on the same broadcast subnet; use `host:` for unicast connection across Docker/VLANs or static IPs.

## Entities
- **Climate**: Grill pit (`heat`, `fan_only`, `off`) and Probe 1 / Probe 2 target temperature controls
- **Sensors**: `Fire State`, `Fire Percentage`, `Warning State`, `Probe 1 Temperature`, `Probe 2 Temperature`
- **Binary Sensors**: `Probe 1 Connected`, `Probe 2 Connected`, `Warning`

## TODO
- [x] Food probe temperature sensors & target temperature climate controls
- [x] Reliable unplugged probe detection (16-bit decoding detects `601 °F` disconnected sentinel vs `<= 257 °F`)
- [x] Warning state sensors (`sensor` + `binary_sensor`)
- [x] Fire state & fire percentage sensors
- [x] 16-bit pit & probe temperature decoding (`> 255 °F`)
- [x] Shared `DataUpdateCoordinator` polling & optional `host` config
- [ ] Test cold smoke mode (`fan_only` / `UK002!`) on live grill
- [ ] Add UI `config_flow` & `DeviceInfo` grouping (Phase 3)

## Test list
- Power on (`UK001!`) - verified
- Power off (`UK004!`) - verified
- Set temp (`UT...`, >= 150 °F) - verified
- Probes & unplugged probe detection (Probe 1 connected / Probe 2 unplugged) - verified on live hardware
- Unit & regression test suite (`tests/test_gmg.py`) - 7/7 passing
