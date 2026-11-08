from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_INTERVAL,
    CONF_MODBUS_ENABLED,
    CONF_MODBUS_PORT,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_INTERVAL,
    DEFAULT_MODBUS_INTERVAL,
    DEFAULT_MODBUS_PORT,
    DOMAIN,
    SENSORS,
)
from .logger_client import DeyeLoggerClient, LoggerError, parse_numeric
from .modbus_client import ModbusError, read_battery_and_grid

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


class DeyeModbusCoordinator(DataUpdateCoordinator):
    """Slow-polling coordinator for battery/grid/load registers (Modbus over
    the logger's local Solarman V5 port). Round trips take ~15-40s, so this
    uses a much longer interval than the HTTP coordinator.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, http_coordinator: DeyeCoordinator):
        d = entry.data
        super().__init__(
            hass, _LOGGER, name=f"{DOMAIN}_modbus",
            update_interval=timedelta(seconds=d.get("modbus_interval", DEFAULT_MODBUS_INTERVAL)),
        )
        self.host = d[CONF_HOST]
        self.port = d.get(CONF_MODBUS_PORT, DEFAULT_MODBUS_PORT)
        self._http_coordinator = http_coordinator

    async def _async_update_data(self):
        serial = (self._http_coordinator.data or {}).get("serial")
        if not serial:
            raise UpdateFailed("logger serial not yet known")
        try:
            return await self.hass.async_add_executor_job(
                read_battery_and_grid, self.host, int(serial), self.port
            )
        except ModbusError as err:
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DeyeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"http": coordinator}

    if entry.data.get(CONF_MODBUS_ENABLED, True):
        modbus_coordinator = DeyeModbusCoordinator(hass, entry, coordinator)
        hass.data[DOMAIN][entry.entry_id]["modbus"] = modbus_coordinator
        # Don't block setup on the (slow, best-effort) modbus registers.
        hass.async_create_task(modbus_coordinator.async_refresh())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
