from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODBUS_SENSORS, SENSORS


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    http_coordinator = coordinators["http"]
    entities = [DeyeSensor(http_coordinator, entry, s) for s in SENSORS]
    modbus_coordinator = coordinators.get("modbus")
    if modbus_coordinator is not None:
        entities += [
            DeyeModbusSensor(modbus_coordinator, http_coordinator, entry, s) for s in MODBUS_SENSORS
        ]
    async_add_entities(entities)


class DeyeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, spec):
        super().__init__(coordinator)
        key, name, _info_key, unit, dev_class, state_class = spec
        serial = coordinator.data.get("serial") if coordinator.data else entry.unique_id
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


class DeyeModbusSensor(CoordinatorEntity, SensorEntity):
    """Battery/grid/load sensor backed by the slow Modbus coordinator.

    Falls back to "unknown" until the first (best-effort) Modbus read
    succeeds, since that coordinator's refresh doesn't block entry setup.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator, http_coordinator, entry, spec):
        super().__init__(coordinator)
        key, name, unit, dev_class, state_class = spec
        serial = http_coordinator.data.get("serial") if http_coordinator.data else entry.unique_id
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
    def available(self):
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)
