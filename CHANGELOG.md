# Changelog

All notable changes to this project will be documented in this file.

## [1.3.4] - 2026-11-27

### Fixed
- **Spike filter fast-ramp handling**: Prevent `_filter_temp_key` in `GmgDataUpdateCoordinator` from freezing readings during sustained fast ramps (e.g., inserting a room-temperature probe into hot meat or rapid pit heat-up) while still suppressing single-poll and erratic out-of-bounds spikes; avoid mutating `grill.state` dicts in place.
- **UDP broadcast discovery resilience**: Catch `OSError` per interface and ignore non-UTF-8 packets in `grills()` so unreachable adapters (Docker bridges, VPNs, loopback) or binary packets on port `8080` do not crash auto-discovery.
- **Status packet retry & sender validation**: Retry up to 5 times in `grill.status()` when a short/corrupted packet is received (not only on socket timeouts), validate sender IP in `grill.send()`, and raise `ValueError` on invalid `probe_number` in `grill.set_temp_probe()`.
- **Probe climate entity contract**: Include `HVACMode.HEAT` in `GmgGrillProbe.hvac_modes`, implement a safe no-op `async_set_hvac_mode`, and return `None` for `native_target_temperature` when probe target is unset (`0`).
- **Pit temperature adjustments while running**: Allow pit target changes whenever `fireState == Running` (`3`) even if pit temperature temporarily dips below `145 °F` (e.g., open lid in cold weather), and raise `HomeAssistantError` instead of failing silently when commands are rejected.

### Changed
- **Config flow & Reconfigure UI**: Added `reconfigure` flow to update grill IP in the UI, pass `updates={CONF_HOST: ...}` on duplicate unique ID checks, preserve `grill_name` during YAML import, and short-circuit `async_step_import` when already configured so HA restarts do not block on UDP discovery.
- **Entity naming**: Enabled `_attr_has_entity_name = True` across climate, sensor, and binary sensor entities for cleaner device-page labels while preserving existing `unique_id`s and entity IDs.
- **Repository hygiene & CI**: Added `.gitignore`, removed tracked `__pycache__/*.pyc` bytecode files from Git, updated `setup.cfg` / `requirements.test.txt`, fixed `tests/test_init.py`, expanded unit test coverage, and added GitHub Actions test workflow.

## [1.3.3] - 2026-11-26

### Fixed
- Prevent transient single/double missed or rejected UDP status polls from flipping all GMG entities to `unavailable`; hold the last known state for up to 2 consecutive missed polls (`MAX_MISSED_POLLS = 3`, ~45 seconds) before marking the grill offline.
- Guard `grill.serial()` and `grill_by_host()` against `UnicodeDecodeError` when non-UTF-8 UDP bytes are received on port 8080.

### Tests
- Added unit tests for `GmgDataUpdateCoordinator` transient missed-poll state retention and `grill_by_host` non-UTF-8 response handling.

## [1.3.2] - 2026-11-26

### Changed
- Set heat-mode food probe `min_temp` to `100 °F` (keeping `32 °F` in cold smoke/off mode).
- Added coordinator-level single-poll temperature spike filtering for pit and food probes.
- Reject short or out-of-range GMG status packets during UDP parsing.
