from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SERIAL, DOMAIN, SENSORS


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(DeyeSensor(coordinator, entry, s) for s in SENSORS)


class DeyeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, spec):
        super().__init__(coordinator)
        key, name, _r, _s, _sg, _o, unit, dev_class, state_class = spec
        serial = entry.data[CONF_SERIAL]
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = dev_class
        self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))}, name=f"Deye {serial}", manufacturer="Deye"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)
