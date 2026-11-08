DOMAIN = "deye_local"
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_INTERVAL = "interval"
DEFAULT_INTERVAL = 2.0

# Modbus (battery/grid/load) registers are read over the logger's local
# Solarman V5 TCP port (8899). Each round trip is slow (~15-40s), so this
# runs on its own, much longer, update interval.
CONF_MODBUS_ENABLED = "modbus_enabled"
CONF_MODBUS_PORT = "modbus_port"
DEFAULT_MODBUS_PORT = 8899
DEFAULT_MODBUS_INTERVAL = 30.0

# Fields parsed from the logger's local status.cgi "inverter.info" array.
# (key, name, info_key, unit, device_class, state_class)
SENSORS = [
    ("current_power", "Current power", "currentPower", "W", "power", "measurement"),
    ("daily_production", "Daily production", "yieldToday", "kWh", "energy", "total_increasing"),
    ("total_production", "Total production", "totalYield", "kWh", "energy", "total_increasing"),
    ("rated_power", "Rated power", "ratedPower", "W", "power", None),
    ("alerts", "Active alerts", "alerts", None, None, "measurement"),
]

# Fields parsed from modbus_client.read_battery_and_grid().
# (key, name, unit, device_class, state_class)
MODBUS_SENSORS = [
    ("battery_voltage", "Battery voltage", "V", "voltage", "measurement"),
    ("battery_soc", "Battery SOC", "%", "battery", "measurement"),
    ("battery_power", "Battery power", "W", "power", "measurement"),
    ("battery_current", "Battery current", "A", "current", "measurement"),
    ("grid_power", "Grid power", "W", "power", "measurement"),
    ("load_power", "Load power", "W", "power", "measurement"),
]
