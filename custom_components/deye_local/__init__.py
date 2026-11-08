from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_HOST, CONF_INTERVAL, CONF_PASSWORD, CONF_USERNAME, DEFAULT_INTERVAL, DOMAIN, SENSORS
from .logger_client import DeyeLoggerClient, LoggerError, parse_numeric

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class DeyeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        d = entry.data
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=d.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        )
        self.client = DeyeLoggerClient(d[CONF_HOST], d[CONF_USERNAME], d[CONF_PASSWORD])

    async def _async_update_data(self):
        try:
            status = await self.hass.async_add_executor_job(self.client.get_status)
        except LoggerError as err:
            raise UpdateFailed(str(err)) from err
        info = {i["key"]: i["value"] for i in status["inverter"]["info"]}
        data = {}
        for key, _name, info_key, *_rest in SENSORS:
            data[key] = parse_numeric(info.get(info_key))
        data["serial"] = status["inverter"]["serialNum"]
        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DeyeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
