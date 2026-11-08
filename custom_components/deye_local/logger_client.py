"""Blocking HTTP client for the Deye Wi-Fi logger's local encrypted CGI API.

Protocol (reverse engineered from the logger's own web UI js/utils.js):
  1. GET require.cgi (base64("require.cgi?t=...") as the path) -> RSA public key PEM.
  2. Generate a random 15-16 digit decimal string as the AES key (also used as IV).
     RSA-encrypt (PKCS1 v1.5) that string and GET send.cgi?key=<base64 ciphertext>
     (path itself base64-encoded, since require/send are the only two "whitelisted"
     unencrypted endpoints) -> "...success..." confirms the device accepted the key.
  3. All further CGI calls: AES-CBC (key used as both key and IV, no padding - the
     plaintext query string is manually zero-padded to a 16 byte boundary) encrypt
     the full "name.cgi?..." query string, base64 it, and GET that as the path.
     The response is base64 ciphertext (trailing "result_end" marker stripped),
     AES-decrypted, zero-padding trimmed, and the JSON payload is wrapped in
     "json_start{...}json_end" markers.
"""
from __future__ import annotations

import base64
import http.client
import json
import random
import time

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA


class LoggerError(Exception):
    pass


def _handle_res_text(t: str):
    s = t.find("json_start")
    e = t.find("json_end")
    if s == -1 or e == -1:
        return t
    s += len("json_start")
    content = t[s:e]
    try:
        return json.loads(content)
    except ValueError:
        return content


class DeyeLoggerClient:
    def __init__(self, host: str, username: str, password: str, timeout: float = 8.0):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self._aes_key: bytes | None = None
        self._logged_in = False

    # -- low level -----------------------------------------------------
    def _raw_get(self, path: str) -> str:
        conn = http.client.HTTPConnection(self.host, 80, timeout=self.timeout)
        try:
            conn.request("GET", "/" + path)
            resp = conn.getresponse()
            return resp.read().decode("utf-8", errors="replace")
        finally:
            conn.close()

    def _unencrypted(self, cgi_with_query: str):
        b64 = base64.b64encode(cgi_with_query.encode()).decode()
        return _handle_res_text(self._raw_get(b64))

    @staticmethod
    def _pad(data: bytes, block: int = 16) -> bytes:
        pad_len = block - (len(data) % block)
        if pad_len == block:
            return data
        return data + b"\x00" * pad_len

    def _handshake(self) -> None:
        pem = self._unencrypted(f"require.cgi?t={random.random()}")
        if not isinstance(pem, str) or "BEGIN PUBLIC KEY" not in pem:
            raise LoggerError(f"unexpected RSA key response: {pem!r}")
        pem_clean = pem.strip("\x00").replace("\r\n", "\n").strip()
        key = RSA.import_key(pem_clean)
        cipher = PKCS1_v1_5.new(key)

        aes_key = str(random.randint(10 ** 15, 10 ** 16 - 1))
        enc = base64.b64encode(cipher.encrypt(aes_key.encode())).decode()
        query = f"send.cgi?key={enc}&t={random.random()}"
        b64 = base64.b64encode(query.encode()).decode()
        result = _handle_res_text(self._raw_get(b64))
        if "success" not in str(result):
            raise LoggerError(f"send.cgi (key exchange) failed: {result!r}")
        self._aes_key = aes_key.encode()

    def _encrypted(self, cgi_with_query: str):
        if self._aes_key is None:
            self._handshake()
        data = self._pad(cgi_with_query.encode())
        cipher = AES.new(self._aes_key, AES.MODE_CBC, iv=self._aes_key)
        ct_b64 = base64.b64encode(cipher.encrypt(data)).decode()
        raw = self._raw_get(ct_b64)
        idx = raw.rfind("result_end")
        body = raw if idx == -1 else raw[:idx]
        try:
            ct2 = base64.b64decode(body)
        except Exception as err:
            raise LoggerError(f"bad base64 response: {raw[:200]!r}") from err
        decipher = AES.new(self._aes_key, AES.MODE_CBC, iv=self._aes_key)
        text = decipher.decrypt(ct2).rstrip(b"\x00").decode("utf-8", errors="replace")
        return _handle_res_text(text)

    # -- high level ------------------------------------------------------
    def login(self) -> None:
        self._aes_key = None  # force a fresh key exchange
        r = self._encrypted(f"login.cgi?user={self.username}&password={self.password}&t={random.random()}")
        if not (isinstance(r, dict) and r.get("status") == "success"):
            raise LoggerError(f"login failed: {r!r}")
        self._logged_in = True

    def get_status(self) -> dict:
        if not self._logged_in:
            self.login()
        try:
            r = self._encrypted(f"status.cgi?t={random.random()}")
        except LoggerError:
            # session likely expired; retry once with a fresh login
            self.login()
            r = self._encrypted(f"status.cgi?t={random.random()}")
        if isinstance(r, dict) and r.get("token_timeout"):
            self.login()
            r = self._encrypted(f"status.cgi?t={random.random()}")
        if not isinstance(r, dict) or "inverter" not in r:
            raise LoggerError(f"unexpected status.cgi response: {r!r}")
        return r


def parse_numeric(value: str) -> float:
    """Turn "123.4 kWh" / "0 W" style strings into a bare float."""
    if value is None:
        return 0.0
    for token in str(value).split():
        try:
            return float(token)
        except ValueError:
            continue
    return 0.0
