"""Blocking client for reading inverter Modbus registers over the logger's
local Solarman V5 TCP port (8899).

Reverse-engineered behaviour of this specific logger/firmware:
  - The V5 "data logging stick" framing is only partially honoured: responses
    arrive fragmented across several small TCP segments with multi-second
    gaps between them (the logger appears to bridge very slowly to the
    inverter's RS485 bus), and the trailing checksum/stop byte is frequently
    never sent at all.
  - Because of that, we do NOT validate the full V5 envelope. Instead we
    collect everything the socket sends for a generous window and scan the
    assembled bytes for a well-formed Modbus RTU response
    (slave id, function code, byte count, data) matching our request -
    this is reliable in practice because every request/response round trip
    uses a brand new TCP connection.
  - A single request/response round trip reliably takes ~10-20 seconds, so
    registers that are needed together must be read in one contiguous block
    read rather than one register at a time.

Register map (single-phase SG0xLP1 family candidate for SG05LP1, see
https://marklabs.pl/en/deye-modbus-complete-register-list/ - confirmed
against this unit by cross-checking battery voltage/current/power
consistency):
  183 Battery Voltage      U_WORD  0.01 V
  184 Battery SOC          U_WORD  1    %
  190 Battery Power        S_WORD  1    W   (+charge / -discharge)
  191 Battery Current      S_WORD  0.01 A   (+charge / -discharge)
  169 Total Grid Power     S_WORD  1    W   (+import / -export)
  167 Inverter/Load Power  S_WORD  1    W   (CT at inverter AC port)
"""
from __future__ import annotations

import socket
import struct
import time


class ModbusError(Exception):
    pass


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def _build_v5_frame(serial: int, seq: int, modbus_pdu: bytes) -> bytes:
    ser = struct.pack("<I", serial)
    # frametype(1) + sensortype(2) + deliverytime(4) + powerontime(4) + offsettime(4)
    payload = b"\x02" + b"\x00" * 14 + modbus_pdu
    inner = struct.pack("<H", 0x4510) + struct.pack("<H", seq) + ser + payload
    frame = b"\xa5" + struct.pack("<H", len(inner)) + inner
    checksum = sum(frame[1:]) & 0xFF
    return frame + bytes([checksum]) + b"\x15"


def _read_block(host: str, port: int, serial: int, seq: int, slave: int, addr: int, qty: int,
                 connect_timeout: float, read_timeout: float, quiet_time: float) -> tuple[int, ...]:
    pdu = bytes([slave, 0x03]) + struct.pack(">HH", addr, qty)
    pdu += struct.pack("<H", _crc16(pdu))
    frame = _build_v5_frame(serial, seq, pdu)

    sock = socket.create_connection((host, port), timeout=connect_timeout)
    try:
        sock.sendall(frame)
        sock.settimeout(0.5)
        start = time.monotonic()
        last_data = start
        buf = b""
        expected_len = 3 + qty * 2 + 2  # slave+func+bytecount + data + crc
        while time.monotonic() - start < read_timeout:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                if buf and (time.monotonic() - last_data) > quiet_time:
                    break
                continue
            if not chunk:
                break
            buf += chunk
            last_data = time.monotonic()
            if len(buf) >= expected_len + 10:
                # plenty of slack collected already, no need to wait further
                break
    finally:
        sock.close()

    header = bytes([slave, 0x03])
    idx = buf.find(header)
    while idx != -1:
        if idx + 3 <= len(buf):
            byte_count = buf[idx + 2]
            data_start = idx + 3
            data_end = data_start + byte_count
            if byte_count == qty * 2 and data_end + 2 <= len(buf):
                data = buf[data_start:data_end]
                crc_recv = struct.unpack("<H", buf[data_end:data_end + 2])[0]
                if _crc16(header + bytes([byte_count]) + data) == crc_recv:
                    return struct.unpack(">" + "H" * qty, data)
        idx = buf.find(header, idx + 1)
    raise ModbusError(f"no valid Modbus response for addr={addr} qty={qty} (got {len(buf)} bytes)")


def read_battery_and_grid(host: str, serial: int, port: int = 8899,
                           connect_timeout: float = 10.0, read_timeout: float = 20.0,
                           quiet_time: float = 2.5) -> dict:
    """Read battery + grid/load registers. Blocking; takes roughly 15-40s total."""
    result: dict[str, float] = {}

    battery = _read_block(host, port, serial, seq=1, slave=1, addr=183, qty=9,
                           connect_timeout=connect_timeout, read_timeout=read_timeout,
                           quiet_time=quiet_time)
    # 183 voltage, 184 soc, 185..189 unused/unknown, 190 power, 191 current
    result["battery_voltage"] = battery[0] * 0.01
    result["battery_soc"] = battery[1]
    result["battery_power"] = _signed16(battery[7])
    result["battery_current"] = _signed16(battery[8]) * 0.01

    grid = _read_block(host, port, serial, seq=2, slave=1, addr=166, qty=7,
                        connect_timeout=connect_timeout, read_timeout=read_timeout,
                        quiet_time=quiet_time)
    # 166 micro-inverter power, 167 inverter/load CT power, 168 unused, 169 total grid power
    result["load_power"] = _signed16(grid[1])
    result["grid_power"] = _signed16(grid[3])

    return result


def _signed16(value: int) -> int:
    return value - 0x10000 if value >= 0x8000 else value
