from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BLOCK_DAILY, BLOCK_MAIN, CONF_INTERVAL, CONF_LISTEN_HOST, CONF_LISTEN_PORT, CONF_SLAVE,
    DEFAULT_INTERVAL, DOMAIN, SENSORS,
)
from .modbus_push import ModbusPushError, ModbusPushServer

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor"]


class DeyeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        d = entry.data
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=d.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        )
        self.server = ModbusPushServer(d[CONF_LISTEN_HOST], d[CONF_LISTEN_PORT], d[CONF_SLAVE])

    async def _async_update_data(self):
        if not self.server.connected:
            # The logger dials in on its own; nothing to read until it does.
            raise UpdateFailed("waiting for logger to connect")
        try:
            regs: dict[int, int] = {}
            for start, count in (BLOCK_MAIN, BLOCK_DAILY):
                for i, v in enumerate(await self.server.read_holding(start, count)):
                    regs[start + i] = v
        except ModbusPushError as err:
            raise UpdateFailed(str(err)) from err
        data = {}
        for key, _n, reg, scale, signed, offset, *_ in SENSORS:
            raw = regs[reg]
            if signed and raw > 0x7FFF:
                raw -= 0x10000
            val = (raw + offset) * scale
            data[key] = round(val, 2) if scale != 1 else int(val)
        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DeyeCoordinator(hass, entry)
    _LOGGER.warning(
        "deye_local: starting push listener on %s:%s (slave=%s)",
        entry.data[CONF_LISTEN_HOST], entry.data[CONF_LISTEN_PORT], entry.data[CONF_SLAVE],
    )
    try:
        await coordinator.server.start()
    except OSError as err:
        _LOGGER.error("deye_local: failed to start listener: %s", err)
        raise
    _LOGGER.warning("deye_local: listener started OK")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_refresh()  # don't block setup if logger hasn't connected yet
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await hass.data[DOMAIN].pop(entry.entry_id).server.stop()
    return ok
