from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_INTERVAL, CONF_LISTEN_HOST, CONF_LISTEN_PORT, CONF_SERIAL, CONF_SLAVE,
    DEFAULT_INTERVAL, DEFAULT_LISTEN_HOST, DEFAULT_PORT, DEFAULT_SLAVE, DOMAIN,
)


class DeyeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Deye logger configured to dial OUT to Home Assistant (logger's Network
    settings -> link2 -> protocol "Modbus Tcp" -> serverMode "Setting" ->
    this host:port). We only open a listening socket here; the logger
    connects to it on its own."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            await self.async_set_unique_id(f"{user_input[CONF_LISTEN_HOST]}:{user_input[CONF_LISTEN_PORT]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Deye {user_input[CONF_SERIAL]}", data=user_input)
        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL): str,
                vol.Optional(CONF_LISTEN_HOST, default=DEFAULT_LISTEN_HOST): str,
                vol.Optional(CONF_LISTEN_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SLAVE, default=DEFAULT_SLAVE): int,
                vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                    vol.Coerce(float), vol.Range(min=0.5, max=60)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
