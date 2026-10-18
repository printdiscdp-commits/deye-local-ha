from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SERIAL, DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DeyeConnectedSensor(coordinator, entry)])


class DeyeConnectedSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = "connectivity"
    _attr_name = "Logger connected"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        serial = entry.data[CONF_SERIAL]
        self._attr_unique_id = f"{serial}_logger_connected"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))}, name=f"Deye {serial}", manufacturer="Deye"
        )

    @property
    def available(self) -> bool:
        # This diagnostic entity must stay available even when the data
        # coordinator's update fails (e.g. "waiting for logger to connect"),
        # otherwise it can never show the disconnected state.
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.server.connected
