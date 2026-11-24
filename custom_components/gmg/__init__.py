"""The Green Mountain Grill integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import GmgDataUpdateCoordinator
from .gmg import grill

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Green Mountain Grill component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Green Mountain Grill from a config entry."""
    host = entry.data[CONF_HOST]
    serial = entry.data.get("serial_number", entry.unique_id or "")

    my_grill = grill(host, serial)
    coordinator = GmgDataUpdateCoordinator(hass, my_grill)
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
