"""The Green Mountain Grill integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_GRILL_NAME, CONF_SERIAL_NUMBER, DOMAIN
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


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when updated (e.g. reconfigure IP)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Green Mountain Grill from a config entry."""
    host = entry.data[CONF_HOST]
    serial = entry.data.get(CONF_SERIAL_NUMBER, entry.unique_id or "")
    grill_name = entry.data.get(CONF_GRILL_NAME)

    my_grill = grill(host, serial)
    coordinator = GmgDataUpdateCoordinator(hass, my_grill, grill_name=grill_name)
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if hasattr(entry, "async_on_unload") and hasattr(entry, "add_update_listener"):
        entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
