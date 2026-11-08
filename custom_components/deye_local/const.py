DOMAIN = "deye_local"
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_INTERVAL = "interval"
DEFAULT_INTERVAL = 2.0

# Fields parsed from the logger's local status.cgi "inverter.info" array.
# (key, name, info_key, unit, device_class, state_class)
SENSORS = [
    ("current_power", "Current power", "currentPower", "W", "power", "measurement"),
    ("daily_production", "Daily production", "yieldToday", "kWh", "energy", "total_increasing"),
    ("total_production", "Total production", "totalYield", "kWh", "energy", "total_increasing"),
    ("rated_power", "Rated power", "ratedPower", "W", "power", None),
    ("alerts", "Active alerts", "alerts", None, None, "measurement"),
]
