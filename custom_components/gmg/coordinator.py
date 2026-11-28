"""Coordinator for Green Mountain Grill."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .gmg import grill

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=15)
MAX_MISSED_POLLS = 3


class GmgDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Class to manage fetching GMG grill data from a single UDP poll."""

    def __init__(
        self,
        hass: HomeAssistant,
        gmg_grill: grill,
        grill_name: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{gmg_grill.serial_number}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.grill = gmg_grill
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, gmg_grill.serial_number)},
            name=grill_name or gmg_grill.serial_number,
            manufacturer="Green Mountain Grills",
            model="GMG Pellet Grill",
        )
        self._last_valid_temps: dict[str, int] = {}
        self._pending_spikes: dict[str, int] = {}
        self._ramp_directions: dict[str, int] = {}
        self._missed_polls = 0

    def _filter_temp_key(self, state: dict, key: str, max_delta: int) -> None:
        """Suppress single-poll temperature spikes while allowing sustained fast ramps."""
        val = state.get(key)
        if val is None:
            return

        prev = self._last_valid_temps.get(key)
        if prev is None:
            self._last_valid_temps[key] = val
            self._pending_spikes.pop(key, None)
            self._ramp_directions.pop(key, None)
            return

        if abs(val - prev) <= max_delta:
            self._last_valid_temps[key] = val
            self._pending_spikes.pop(key, None)
            self._ramp_directions.pop(key, None)
            return

        pending = self._pending_spikes.get(key)
        if pending is not None:
            direction = 1 if pending > prev else -1
            if abs(val - pending) <= max_delta or (
                (val - prev) * direction > 0 and abs(val - pending) <= max_delta * 2
            ):
                self._last_valid_temps[key] = val
                self._pending_spikes.pop(key, None)
                self._ramp_directions[key] = direction
                return

        ramp_dir = self._ramp_directions.get(key)
        if (
            ramp_dir is not None
            and (val - prev) * ramp_dir > 0
            and abs(val - prev) <= max_delta * 2
        ):
            self._last_valid_temps[key] = val
            return

        _LOGGER.debug(
            "Suppressing single-poll %s spike: %s -> %s (holding %s)",
            key,
            prev,
            val,
            prev,
        )
        self._ramp_directions.pop(key, None)
        self._pending_spikes[key] = val
        state[key] = prev

    def _filter_spikes(self, state: dict) -> dict:
        """Filter single-poll sensor glitches from pit and food probe temperatures."""
        if not state:
            return state

        filtered = dict(state)
        self._filter_temp_key(filtered, "temp", max_delta=35)

        for probe_idx in (1, 2):
            key = f"probe{probe_idx}_temp"
            if filtered.get(f"probe{probe_idx}_connected"):
                self._filter_temp_key(filtered, key, max_delta=15)
            else:
                self._last_valid_temps.pop(key, None)
                self._pending_spikes.pop(key, None)
                self._ramp_directions.pop(key, None)

        return filtered

    async def _async_update_data(self) -> dict:
        """Fetch latest status from the grill."""
        state = await self.hass.async_add_executor_job(self.grill.status)
        if not state:
            self._missed_polls += 1
            if self.data and self._missed_polls < MAX_MISSED_POLLS:
                _LOGGER.debug(
                    "Empty status from grill %s (%s/%s missed polls); holding last known state",
                    self.grill.serial_number,
                    self._missed_polls,
                    MAX_MISSED_POLLS,
                )
                return self.data

            self._last_valid_temps.clear()
            self._pending_spikes.clear()
            self._ramp_directions.clear()
            return {}

        self._missed_polls = 0
        return self._filter_spikes(state)
