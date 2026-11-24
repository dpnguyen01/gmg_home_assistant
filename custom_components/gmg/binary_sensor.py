"""Green Mountain Grill binary_sensor platform."""

from typing import Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GmgDataUpdateCoordinator


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up GMG binary sensors from discovery_info."""
    if not discovery_info:
        return

    serial = discovery_info.get("serial")
    coordinator: Optional[GmgDataUpdateCoordinator] = hass.data.get(DOMAIN, {}).get(serial)
    if coordinator is None:
        return

    entities: list[BinarySensorEntity] = [
        GmgProbeConnectedBinarySensor(coordinator, 1),
        GmgProbeConnectedBinarySensor(coordinator, 2),
        GmgWarningBinarySensor(coordinator),
    ]
    async_add_entities(entities)


class GmgBaseBinarySensor(
    CoordinatorEntity[GmgDataUpdateCoordinator], BinarySensorEntity
):
    """Base binary sensor for GMG grill."""

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._serial = coordinator.grill.serial_number

    @property
    def _state(self) -> dict:
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._state)


class GmgProbeConnectedBinarySensor(GmgBaseBinarySensor):
    """Binary sensor indicating whether a food probe is plugged in."""

    _attr_device_class = BinarySensorDeviceClass.PLUG

    def __init__(
        self, coordinator: GmgDataUpdateCoordinator, probe_number: int
    ) -> None:
        super().__init__(coordinator)
        self._probe_number = probe_number
        self._attr_unique_id = f"{self._serial}_probe_{probe_number}_connected"
        self._attr_name = f"{self._serial} Probe {probe_number} Connected"

    @property
    def is_on(self) -> bool:
        return bool(self._state.get(f"probe{self._probe_number}_connected", False))


class GmgWarningBinarySensor(GmgBaseBinarySensor):
    """Binary sensor indicating whether the grill has an active warning."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._serial}_warning"
        self._attr_name = f"{self._serial} Warning"

    @property
    def is_on(self) -> bool:
        return self._state.get("warnState", 0) != 0
