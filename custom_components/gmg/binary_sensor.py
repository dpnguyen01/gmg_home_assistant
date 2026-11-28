"""Green Mountain Grill binary_sensor platform."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GmgDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up GMG binary sensors from a config entry."""
    coordinator: GmgDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
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

    _attr_has_entity_name = True

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._serial = coordinator.grill.serial_number
        self._attr_device_info = coordinator.device_info

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
        self._attr_name = f"Probe {probe_number} Connected"

    @property
    def is_on(self) -> bool:
        return bool(self._state.get(f"probe{self._probe_number}_connected", False))


class GmgWarningBinarySensor(GmgBaseBinarySensor):
    """Binary sensor indicating whether the grill has an active warning."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Warning"

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._serial}_warning"

    @property
    def is_on(self) -> bool:
        return self._state.get("warnState", 0) != 0
