"""Green Mountain Grill sensor platform."""

from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FIRE_STATES, WARN_STATES
from .coordinator import GmgDataUpdateCoordinator


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up GMG sensors from discovery_info."""
    if not discovery_info:
        return

    serial = discovery_info.get("serial")
    coordinator: Optional[GmgDataUpdateCoordinator] = hass.data.get(DOMAIN, {}).get(serial)
    if coordinator is None:
        return

    entities: list[SensorEntity] = [
        GmgFireStateSensor(coordinator),
        GmgFirePercentageSensor(coordinator),
        GmgWarnStateSensor(coordinator),
        GmgProbeTemperatureSensor(coordinator, 1),
        GmgProbeTemperatureSensor(coordinator, 2),
    ]
    async_add_entities(entities)


class GmgBaseSensor(CoordinatorEntity[GmgDataUpdateCoordinator], SensorEntity):
    """Base sensor for GMG grill."""

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._serial = coordinator.grill.serial_number

    @property
    def _state(self) -> dict:
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._state)


class GmgFireStateSensor(GmgBaseSensor):
    """Fire state sensor for GMG grill."""

    _attr_icon = "mdi:fire"

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._serial}_fire_state"
        self._attr_name = f"{self._serial} Fire State"

    @property
    def native_value(self) -> Optional[str]:
        val = self._state.get("fireState")
        if val is None:
            return None
        return FIRE_STATES.get(val, f"Unknown ({val})")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"raw_value": self._state.get("fireState")}


class GmgFirePercentageSensor(GmgBaseSensor):
    """Fire percentage (auger/fan duty) sensor for GMG grill."""

    _attr_icon = "mdi:fire-circle"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._serial}_fire_percentage"
        self._attr_name = f"{self._serial} Fire Percentage"

    @property
    def native_value(self) -> Optional[int]:
        return self._state.get("fireStatePercentage")


class GmgWarnStateSensor(GmgBaseSensor):
    """Warning state sensor for GMG grill."""

    _attr_icon = "mdi:alert-outline"

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._serial}_warn_state"
        self._attr_name = f"{self._serial} Warning State"

    @property
    def native_value(self) -> Optional[str]:
        val = self._state.get("warnState")
        if val is None:
            return None
        return WARN_STATES.get(val, f"Warning ({val})")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"raw_value": self._state.get("warnState")}


class GmgProbeTemperatureSensor(GmgBaseSensor):
    """Temperature sensor for a GMG food probe."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-lines"

    def __init__(
        self, coordinator: GmgDataUpdateCoordinator, probe_number: int
    ) -> None:
        super().__init__(coordinator)
        self._probe_number = probe_number
        self._attr_unique_id = f"{self._serial}_probe_{probe_number}_temperature"
        self._attr_name = f"{self._serial} Probe {probe_number} Temperature"

    @property
    def native_value(self) -> Optional[int]:
        if not self._state.get(f"probe{self._probe_number}_connected", False):
            return None
        return self._state.get(f"probe{self._probe_number}_temp")
