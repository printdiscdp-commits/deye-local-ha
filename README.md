# Deye Local (push Modbus TCP)

Local, low-latency Home Assistant integration for Deye hybrid inverters (SG0*LP1 series)
whose Wi-Fi logger firmware does NOT expose the classic Solarman V5 port 8899/502.

Instead, this works with loggers that support **Network settings -> link2 -> protocol
"Modbus Tcp" -> serverMode "Setting"**: the logger dials OUT to a configured host:port
and then behaves as a Modbus TCP slave on that single persistent connection.

This integration starts a small TCP listener in Home Assistant, accepts that one
inbound connection from the logger, and polls holding registers over it (default
every 1 second).

## Requirements

- Logger's web UI (port 80) -> Network settings -> link2:
  - Enable: Enable
  - Protocol: Modbus Tcp
  - Server mode: Setting
  - IP address: <your Home Assistant host IP>
  - Port: 8899 (or any free port)
- Home Assistant host must allow **inbound** TCP on that port (firewall).

## Installation (HACS)

1. HACS -> Integrations -> the three-dot menu (top right) -> Custom repositories.
2. Add this repository URL, category "Integration".
3. Find "Deye Local (Solarman V5)" in HACS and install.
4. Restart Home Assistant.
5. Settings -> Devices & services -> Add integration -> "Deye Local".
   - Serial: your inverter/logger serial number
   - Listen host: 0.0.0.0
   - Listen port: must match the port set in link2 above
   - Slave: 1 (default)
   - Interval: 1 (seconds)

## Entities

- Battery SOC / voltage / temperature / power
- Grid voltage / frequency / power
- Load power
- PV1 / PV2 power, voltage, current
- Daily production
- "Logger connected" binary sensor

Register map is based on the Deye Modbus protocol V1.18 for SG0*LP1 hybrid inverters;
adjust `const.py` if your model differs.
