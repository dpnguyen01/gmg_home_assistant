"""Coordinator for Green Mountain Grill."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .gmg import grill

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=15)


class GmgDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Class to manage fetching GMG grill data from a single UDP poll."""

    def __init__(self, hass: HomeAssistant, gmg_grill: grill) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{gmg_grill.serial_number}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.grill = gmg_grill

    async def _async_update_data(self) -> dict:
        """Fetch latest status from the grill."""
        return await self.hass.async_add_executor_job(self.grill.status)
