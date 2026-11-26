"""Green Mountain Grill climate platform."""

import logging
from typing import List, Optional

import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GmgDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional("grill_name"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Import legacy YAML platform config into a config entry."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=dict(config),
        )
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up GMG climate entities from a config entry."""
    coordinator: GmgDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GmgGrill(coordinator),
        GmgGrillProbe(coordinator, 1),
        GmgGrillProbe(coordinator, 2),
    ]
    async_add_entities(entities)


class GmgGrill(CoordinatorEntity[GmgDataUpdateCoordinator], ClimateEntity):
    """Representation of a Green Mountain Grill smoker."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: GmgDataUpdateCoordinator) -> None:
        """Initialize the Grill."""
        super().__init__(coordinator)
        self._grill = coordinator.grill
        self._unique_id = f"{self._grill.serial_number}"
        self._attr_device_info = coordinator.device_info

    @property
    def _state(self) -> dict:
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        """Return True if grill state was retrieved."""
        return super().available and bool(self._state)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        if temperature == self._state.get("grill_set_temp"):
            return

        if self._state.get("on", 0) == 0:
            _LOGGER.warning("Grill is not on, cannot set temperature")
            return

        if self._state.get("temp", 0) < 145:
            _LOGGER.warning(
                "Grill is not 150 F, cannot set temperature. Temp is %s",
                self._state.get("temp"),
            )
            return

        try:
            _LOGGER.debug("Setting temperature to %s", temperature)
            await self.hass.async_add_executor_job(
                self._grill.set_temp, int(temperature)
            )
            await self.coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Error setting temperature: %s", temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the operation mode."""
        if hvac_mode == HVACMode.HEAT:
            await self.hass.async_add_executor_job(self._grill.power_on)
        elif hvac_mode == HVACMode.OFF:
            await self.hass.async_add_executor_job(self._grill.power_off)
        elif hvac_mode == HVACMode.FAN_ONLY:
            await self.hass.async_add_executor_job(self._grill.power_on_cool)
        else:
            _LOGGER.error("Unsupported hvac mode: %s", hvac_mode)
            return

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn device off."""
        await self.hass.async_add_executor_job(self._grill.power_off)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self.hass.async_add_executor_job(self._grill.power_on)
        await self.coordinator.async_request_refresh()

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

    @property
    def icon(self) -> str:
        return "mdi:grill"

    @property
    def hvac_modes(self) -> List[HVACMode]:
        """Return the supported operations."""
        return [HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC operation."""
        on_state = self._state.get("on")
        if on_state == 1:
            return HVACMode.HEAT
        if on_state == 2:
            return HVACMode.FAN_ONLY
        return HVACMode.OFF

    @property
    def name(self) -> str:
        """Return unique ID of grill which is GMGSERIAL_NUMBER."""
        return self._unique_id

    @property
    def native_temperature_unit(self) -> str:
        """Return the unit of measurement for the grill."""
        return UnitOfTemperature.FAHRENHEIT

    @property
    def native_current_temperature(self) -> Optional[float]:
        """Return current temp of the grill."""
        return self._state.get("temp")

    @property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temp."""
        return 5

    @property
    def native_target_temperature(self) -> Optional[float]:
        """Return what the temp is set to go to."""
        return self._state.get("grill_set_temp")

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return self._grill.MAX_TEMP_F

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return self._grill.MIN_TEMP_F

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id


class GmgGrillProbe(CoordinatorEntity[GmgDataUpdateCoordinator], ClimateEntity):
    """Representation of a Green Mountain Grill smoker food probe."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self, coordinator: GmgDataUpdateCoordinator, probe_count: int
    ) -> None:
        """Initialize the Grill Probe."""
        super().__init__(coordinator)
        self._grill = coordinator.grill
        self._probe_count = probe_count
        self._unique_id = f"{self._grill.serial_number}_probe_{probe_count}"
        self._attr_device_info = coordinator.device_info

    @property
    def _state(self) -> dict:
        return self.coordinator.data or {}

    @property
    def _is_connected(self) -> bool:
        return bool(self._state.get(f"probe{self._probe_count}_connected", False))

    @property
    def available(self) -> bool:
        """Return True if grill state was retrieved."""
        return super().available and bool(self._state)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        if temperature == self._state.get(f"probe{self._probe_count}_set_temp"):
            return

        if self._state.get("on", 0) == 0:
            _LOGGER.error("Grill is not on, cannot set temperature")
            return

        try:
            _LOGGER.debug("Setting probe %s temperature to %s", self._probe_count, temperature)
            await self.hass.async_add_executor_job(
                self._grill.set_temp_probe, int(temperature), self._probe_count
            )
            await self.coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Error setting probe temperature: %s", temperature)

    @property
    def hvac_modes(self) -> List[HVACMode]:
        """Return the supported operations."""
        return [HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC operation."""
        if self._state.get("on") == 1 and self._is_connected:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def icon(self) -> str:
        return "mdi:thermometer-lines"

    @property
    def name(self) -> str:
        """Return unique ID of grill probe."""
        return self._unique_id

    @property
    def native_temperature_unit(self) -> str:
        """Return the unit of measurement for the probe."""
        return UnitOfTemperature.FAHRENHEIT

    @property
    def native_current_temperature(self) -> Optional[float]:
        """Return current temp of the probe, or None when unplugged."""
        if not self._is_connected:
            return None
        return self._state.get(f"probe{self._probe_count}_temp")

    @property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temp."""
        return 1

    @property
    def native_target_temperature(self) -> Optional[float]:
        """Return what the temp is set to go to."""
        if not self._is_connected:
            return None
        return self._state.get(f"probe{self._probe_count}_set_temp")

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return self._grill.MAX_TEMP_F_PROBE

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature based on heat vs cold smoke/off mode."""
        if self._state.get("on") == 1:
            return self._grill.MIN_TEMP_F_PROBE_HEAT
        return self._grill.MIN_TEMP_F_PROBE

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id
