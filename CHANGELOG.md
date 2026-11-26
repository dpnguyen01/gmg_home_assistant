# Changelog

All notable changes to this project will be documented in this file.

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
