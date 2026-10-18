"""Minimal Modbus-TCP master logic over a connection the Deye logger itself opens.

The Deye Wi-Fi logger (firmware with "Modbus Tcp" / serverMode "Setting" under
Network settings) dials OUT to a configured host:port and then behaves as a
Modbus TCP slave on that single persistent socket. We therefore run a small
TCP server, accept that one inbound connection, and act as the Modbus master
over it (standard MBAP framing, function 0x03 Read Holding Registers).
"""
from __future__ import annotations

import asyncio
import logging
import struct

_LOGGER = logging.getLogger(__name__)


class ModbusPushError(Exception):
    pass


class ModbusPushServer:
    """Accepts the logger's inbound connection and issues Modbus TCP reads."""

    def __init__(self, host: str, port: int, slave: int = 1, timeout: float = 5.0):
        self._host = host
        self._port = port
        self.slave = slave
        self.timeout = timeout
        self._server: asyncio.base_events.Server | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._txid = 0
        self._peer: str | None = None

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    @property
    def peer(self) -> str | None:
        return self._peer

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._on_connect, self._host, self._port)

    async def stop(self) -> None:
        if self._writer:
            self._writer.close()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _on_connect(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        _LOGGER.warning("deye_local: inbound connection accepted from %s", peer)
        if self._writer and not self._writer.is_closing():
            # Replace a stale connection with the fresh one.
            self._writer.close()
        self._reader, self._writer, self._peer = reader, writer, str(peer)

    async def read_holding(self, start: int, count: int) -> list[int]:
        async with self._lock:
            if not self.connected or self._reader is None:
                raise ModbusPushError("logger not connected yet")
            self._txid = (self._txid + 1) & 0xFFFF
            pdu = struct.pack(">BHH", 0x03, start, count)
            mbap = struct.pack(">HHHB", self._txid, 0, len(pdu) + 1, self.slave)
            try:
                self._writer.write(mbap + pdu)
                await self._writer.drain()
                head = await asyncio.wait_for(self._reader.readexactly(7), self.timeout)
                r_txid, r_proto, r_len, r_unit = struct.unpack(">HHHB", head)
                body = await asyncio.wait_for(self._reader.readexactly(r_len - 1), self.timeout)
            except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
                self._writer = None
                raise ModbusPushError(str(err) or type(err).__name__) from err
            if r_txid != self._txid:
                raise ModbusPushError("transaction id mismatch")
            func = body[0]
            if func & 0x80:
                raise ModbusPushError(f"modbus exception code {body[1] if len(body) > 1 else '?'}")
            byte_count = body[1]
            regs = body[2 : 2 + byte_count]
            if len(regs) != count * 2:
                raise ModbusPushError("unexpected register payload length")
            return list(struct.unpack(f">{count}H", regs))
