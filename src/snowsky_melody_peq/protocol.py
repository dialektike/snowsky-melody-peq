"""Low-level USB HID packet framing for FiiO devices.

Protocol spec (reverse-engineered from FiiO Control APK v4.0.3):

  GET request : [0xBB, 0x0B, 0x00, 0x00, CMD, LEN, ...DATA, 0x00, 0xEE]
  SET request : [0xAA, 0x0A, 0x00, 0x00, CMD, LEN, ...DATA, 0x00, 0xEE]
  GET response: [0xBB, 0x0B, 0x00, 0x00, CMD, LEN, ...DATA, 0x00, 0xEE]

The packet is then wrapped into a USB HID OUT report with Report ID 0x07
and padded to 65 bytes (1-byte report ID + 64-byte payload).

EQ command codes (single byte):
    0x15  EQ_BAND        per-band parameters
    0x16  EQ_PRESET      preset selection
    0x17  EQ_GAIN        global pre-amp gain
    0x18  EQ_COUNT       supported band count (GET-only)
    0x19  EQ_SAVE        persist current EQ to USER slot
    0x1A  EQ_SWITCH      EQ on/off
    0x1B  EQ_RESET       clear current slot
    0x30  PRESET_NAME    preset display name
"""

from __future__ import annotations

# ─── USB descriptor constants ──────────────────────────────
VENDOR_ID  = 0x2972
INTERFACE  = 3
EP_OUT     = 0x02
EP_IN      = 0x83
REPORT_ID  = 0x07
HID_REPORT_SIZE = 65   # 1 report-ID byte + 64 payload bytes
TIMEOUT_MS = 300

# ─── Packet framing ────────────────────────────────────────
GET_HEAD,  GET_START = 0xBB, 0x0B
SET_HEAD,  SET_START = 0xAA, 0x0A
STOP                 = 0xEE


class CMD:
    """USB HID EQ command codes."""
    EQ_BAND     = 0x15
    EQ_PRESET   = 0x16
    EQ_GAIN     = 0x17
    EQ_COUNT    = 0x18
    EQ_SAVE     = 0x19
    EQ_SWITCH   = 0x1A
    EQ_RESET    = 0x1B
    PRESET_NAME = 0x30


# ─── Numeric encoders/decoders ─────────────────────────────

def encode_gain(db: float) -> tuple[int, int]:
    """dB → i16 BE, ×10. Range -24.0 .. +12.0 typical."""
    raw = int(round(db * 10)) & 0xFFFF
    return (raw >> 8) & 0xFF, raw & 0xFF

def decode_gain(b1: int, b2: int) -> float:
    raw = (b1 << 8) | b2
    return -((raw ^ 0xFFFF) + 1) / 10.0 if raw & 0x8000 else raw / 10.0

def encode_u16(v: int) -> tuple[int, int]:
    return (v >> 8) & 0xFF, v & 0xFF

def decode_u16(b1: int, b2: int) -> int:
    return (b1 << 8) | b2


# ─── Packet builders ───────────────────────────────────────

def build_get(cmd: int, data: bytes = b"") -> bytes:
    """Build a GET request packet (header 0xBB 0x0B)."""
    return bytes([GET_HEAD, GET_START, 0, 0, cmd, len(data)]) + data + bytes([0, STOP])

def build_set(cmd: int, data: bytes = b"") -> bytes:
    """Build a SET request packet (header 0xAA 0x0A)."""
    return bytes([SET_HEAD, SET_START, 0, 0, cmd, len(data)]) + data + bytes([0, STOP])

def wrap_hid_report(packet: bytes, size: int = HID_REPORT_SIZE) -> bytes:
    """Wrap a protocol packet in a USB HID OUT report.

    Layout: [Report ID, ...packet bytes, zero padding to `size`].
    """
    buf = bytearray(size)
    buf[0] = REPORT_ID
    payload = packet[: size - 1]
    buf[1 : 1 + len(payload)] = payload
    return bytes(buf)


# ─── Response parsing ──────────────────────────────────────

def strip_report_id(resp: bytes) -> bytes:
    """Remove leading Report ID byte if present."""
    return resp[1:] if resp and resp[0] == REPORT_ID else resp

def parse_response(resp: bytes) -> tuple[int, bytes] | None:
    """Extract (cmd, payload) from a response packet, or None if malformed."""
    resp = strip_report_id(resp)
    if len(resp) < 6 or resp[0] not in (GET_HEAD, SET_HEAD):
        return None
    cmd  = resp[4]
    dlen = resp[5]
    if 6 + dlen > len(resp):
        return None
    return cmd, bytes(resp[6 : 6 + dlen])
