from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import CONF_HOST, CONF_INTERVAL, CONF_PASSWORD, CONF_USERNAME, DEFAULT_INTERVAL, DOMAIN
from .logger_client import DeyeLoggerClient, LoggerError


class DeyeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Polls the logger's local encrypted web API (same credentials as its
    web UI) over plain HTTP, port 80 - no special network/firewall setup
    needed beyond normal LAN access from Home Assistant to the logger."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            client = DeyeLoggerClient(
                user_input[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            try:
                status = await self.hass.async_add_executor_job(client.get_status)
            except LoggerError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                serial = status["inverter"]["serialNum"]
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Deye {serial}", data=user_input)
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=60)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
