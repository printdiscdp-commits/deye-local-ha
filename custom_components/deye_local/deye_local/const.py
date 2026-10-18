DOMAIN = "deye_local"
CONF_SERIAL = "serial"
CONF_SLAVE = "slave"
CONF_INTERVAL = "interval"
CONF_LISTEN_HOST = "listen_host"
CONF_LISTEN_PORT = "listen_port"
DEFAULT_LISTEN_HOST = "0.0.0.0"
DEFAULT_PORT = 8899
DEFAULT_SLAVE = 1
DEFAULT_INTERVAL = 1.0

# Hybrid single-phase Deye (SUN-xK-SG01LP1 / SG02LP1) holding registers.
# (key, name, register, scale, signed, offset, unit, device_class, state_class)
# Registers differ between models; adjust to your inverter's Modbus table.
BLOCK_MAIN = (586, 94)  # 586..679
BLOCK_DAILY = (502, 1)

SENSORS = [
    ("battery_temp", "Battery temperature", 586, 0.1, False, -1000, "°C", "temperature", "measurement"),
    ("battery_voltage", "Battery voltage", 587, 0.1, False, 0, "V", "voltage", "measurement"),
    ("battery_soc", "Battery SOC", 588, 1, False, 0, "%", "battery", "measurement"),
    ("battery_power", "Battery power", 590, 1, True, 0, "W", "power", "measurement"),
    ("grid_voltage", "Grid voltage", 598, 0.1, False, 0, "V", "voltage", "measurement"),
    ("grid_frequency", "Grid frequency", 609, 0.01, False, 0, "Hz", "frequency", "measurement"),
    ("grid_power", "Grid power", 625, 1, True, 0, "W", "power", "measurement"),
    ("load_power", "Load power", 653, 1, False, 0, "W", "power", "measurement"),
    ("pv1_power", "PV1 power", 672, 1, False, 0, "W", "power", "measurement"),
    ("pv2_power", "PV2 power", 673, 1, False, 0, "W", "power", "measurement"),
    ("pv1_voltage", "PV1 voltage", 676, 0.1, False, 0, "V", "voltage", "measurement"),
    ("pv1_current", "PV1 current", 677, 0.1, False, 0, "A", "current", "measurement"),
    ("pv2_voltage", "PV2 voltage", 678, 0.1, False, 0, "V", "voltage", "measurement"),
    ("pv2_current", "PV2 current", 679, 0.1, False, 0, "A", "current", "measurement"),
    ("daily_production", "Daily production", 502, 0.1, False, 0, "kWh", "energy", "total_increasing"),
]
