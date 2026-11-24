"""Config flow for Green Mountain Grill integration."""

from typing import Any, Optional

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import DOMAIN
from .gmg import grill_by_host, grills

CONF_SERIAL_NUMBER = "serial_number"


class GmgConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Green Mountain Grill."""

    VERSION = 1

    async def _discover_grill(self, host: Optional[str]):
        """Discover a GMG grill by host IP or UDP broadcast."""
        if host:
            return await self.hass.async_add_executor_job(grill_by_host, host.strip(), 2)
        found = await self.hass.async_add_executor_job(grills, 2)
        return found[0] if found else None

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = (user_input.get(CONF_HOST) or "").strip() or None
            my_grill = await self._discover_grill(host)

            if my_grill is None:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(my_grill.serial_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=my_grill.serial_number,
                    data={
                        CONF_HOST: my_grill.ip,
                        CONF_SERIAL_NUMBER: my_grill.serial_number,
                    },
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_HOST, default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Import configuration from legacy configuration.yaml."""
        host = (import_data.get(CONF_HOST) or "").strip() or None
        my_grill = await self._discover_grill(host)
        if my_grill is None:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(my_grill.serial_number)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=my_grill.serial_number,
            data={
                CONF_HOST: my_grill.ip,
                CONF_SERIAL_NUMBER: my_grill.serial_number,
            },
        )
