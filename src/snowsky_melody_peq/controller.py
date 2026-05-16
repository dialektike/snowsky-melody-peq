"""SnowSky Melody PEQ device controller.

This controller is intentionally locked to the SnowSky Melody. On open, it
verifies that the connected USB device identifies itself as a Melody, and
refuses to talk to anything else. This is a safety choice: although other
FiiO devices share the USB HID EQ protocol, only the Melody has been
designated as in-scope for this library.

The library uses ``hidapi`` to access the device through the OS HID stack,
which avoids the WinUSB driver replacement that a raw libusb backend would
require on Windows.
"""

from __future__ import annotations

import re
import time
from typing import Any

import hid

from .protocol import (
    CMD,
    HID_REPORT_SIZE,
    TIMEOUT_MS,
    VENDOR_ID,
    build_get,
    build_set,
    decode_gain,
    decode_u16,
    encode_gain,
    encode_u16,
    parse_response,
    wrap_hid_report,
)
from .types import Band, FilterType

# ─── Melody identity ──────────────────────────────────────────
# The HID product string is matched case-insensitively as a whole word, so
# that "SnowSky Melody" matches but a hypothetical future "MelodyControl"
# or "MelodyEdition K3" would not. Add to this tuple if FiiO ships the
# Melody with a slightly different product string (firmware variants,
# regional SKUs).
MELODY_PRODUCT_KEYWORDS: tuple[str, ...] = ("melody",)
_MELODY_PRODUCT_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in MELODY_PRODUCT_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def _is_melody_product_string(s: str | None) -> bool:
    if not s:
        return False
    return _MELODY_PRODUCT_RE.search(s) is not None

# Known Melody capabilities.
MELODY_USER_SLOTS = (1, 2, 3)         # USER1..USER3 → preset IDs 160..162
MELODY_PRESET_USER1 = 160
MELODY_PRESET_BYPASS = 240


# ─── Exceptions ───────────────────────────────────────────────

class MelodyPEQError(RuntimeError):
    """Base error for Melody device communication."""


class NotAMelodyError(MelodyPEQError):
    """Raised when the only attached FiiO device is not a SnowSky Melody."""


# ─── Controller ───────────────────────────────────────────────

class MelodyPEQ:
    """HID controller for the FiiO SnowSky Melody.

    Use as a context manager:

        with MelodyPEQ() as dev:
            for band in dev.get_all_bands():
                print(band)

    Parameters
    ----------
    inter_cmd_delay : float, optional
        Seconds to sleep between sequential commands in batch operations.
        Default 0.03 s. Increase if you see lost responses.

    Raises
    ------
    MelodyPEQError
        No FiiO HID device found, or the device cannot be opened.
    NotAMelodyError
        A FiiO HID device was found, but its product string did not identify
        it as a SnowSky Melody.
    """

    def __init__(self, inter_cmd_delay: float = 0.03):
        if inter_cmd_delay < 0:
            raise ValueError(
                f"inter_cmd_delay must be non-negative, got {inter_cmd_delay}"
            )
        self.inter_cmd_delay = inter_cmd_delay
        self._dev: Any | None = None
        self._product_name: str = ""

    # ── context manager ──
    def __enter__(self) -> MelodyPEQ:
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ── connection lifecycle ──
    def open(self) -> None:
        candidates = hid.enumerate(VENDOR_ID, 0) or []
        if not candidates:
            raise MelodyPEQError(
                f"No FiiO HID device found (VID=0x{VENDOR_ID:04X}). "
                f"Check that the Melody is connected and powered."
            )

        melody_info = next(
            (
                info for info in candidates
                if _is_melody_product_string(info.get("product_string"))
            ),
            None,
        )
        if melody_info is None:
            names = [info.get("product_string") or "<unnamed>" for info in candidates]
            raise NotAMelodyError(
                f"Connected FiiO device(s) are not a SnowSky Melody: {names}. "
                f"This library only supports the Melody."
            )

        self._product_name = melody_info.get("product_string") or ""
        device = hid.device()
        try:
            device.open_path(melody_info["path"])
        except OSError as e:
            raise MelodyPEQError(
                f"Failed to open Melody HID device: {e}. "
                f"On Linux, check udev rules; on Windows, close any other app "
                f"holding the device (e.g. FiiO Control)."
            ) from e
        self._dev = device

    def close(self) -> None:
        if self._dev is None:
            return
        try:
            self._dev.close()
        except Exception:
            pass
        self._dev = None
        self._product_name = ""

    @property
    def name(self) -> str:
        return self._product_name

    # ── low-level transport ──
    def _drain(self) -> None:
        if self._dev is None:
            return
        try:
            while True:
                data = self._dev.read(HID_REPORT_SIZE, timeout_ms=10)
                if not data:
                    break
        except OSError:
            pass

    def _exchange(self, packet: bytes, expect_cmd: int) -> bytes | None:
        if self._dev is None:
            raise MelodyPEQError("Device not open. Call .open() or use 'with'.")
        self._drain()
        # hidapi's write() expects the report ID as the first byte, which
        # wrap_hid_report() already provides.
        self._dev.write(wrap_hid_report(packet))
        for _ in range(2):
            data = self._dev.read(HID_REPORT_SIZE, timeout_ms=TIMEOUT_MS)
            if not data:
                return None
            raw = bytes(data)
            parsed = parse_response(raw)
            if parsed and parsed[0] == expect_cmd:
                return raw
        return None

    def _get(self, cmd: int, data: bytes = b"") -> bytes | None:
        return self._exchange(build_get(cmd, data), cmd)

    def _set(self, cmd: int, data: bytes = b"") -> bytes | None:
        return self._exchange(build_set(cmd, data), cmd)

    # ─────────────────────────── GET API ───────────────────────────
    #
    # Getters return ``None`` when the device does not answer the query, so
    # that callers can distinguish a real device value (e.g. "EQ off",
    # "0 bands") from a missing response. Verified on real hardware: the
    # SnowSky Melody does not respond to ``CMD.EQ_SWITCH`` (0x1A) GET/SET,
    # so ``get_eq_enabled()`` returns ``None`` on Melody.

    def get_band_count(self) -> int | None:
        """Number of PEQ bands the Melody supports, or None if not answered.

        Queried from the device rather than assumed, since firmware updates
        may change this.
        """
        resp = self._get(CMD.EQ_COUNT)
        p = parse_response(resp) if resp else None
        return p[1][0] if p and p[1] else None

    def get_eq_enabled(self) -> bool | None:
        """EQ on/off, or None if the device did not respond."""
        resp = self._get(CMD.EQ_SWITCH)
        p = parse_response(resp) if resp else None
        return bool(p[1][0]) if p and p[1] else None

    def get_preset(self) -> int | None:
        """Current preset ID, or None if not answered.

        Known values: 160-162 = USER1..USER3, 240 = bypass.
        """
        resp = self._get(CMD.EQ_PRESET)
        p = parse_response(resp) if resp else None
        return p[1][0] if p and p[1] else None

    def get_preamp(self) -> float | None:
        """Global pre-amp gain in dB, or None if not answered."""
        resp = self._get(CMD.EQ_GAIN)
        p = parse_response(resp) if resp else None
        return decode_gain(p[1][0], p[1][1]) if p and len(p[1]) >= 2 else None

    def get_band(self, index: int) -> Band | None:
        resp = self._get(CMD.EQ_BAND, bytes([index]))
        p = parse_response(resp) if resp else None
        if not p or len(p[1]) < 8:
            return None
        d = p[1]
        return Band(
            index       = d[0],
            gain        = decode_gain(d[1], d[2]),
            freq        = decode_u16(d[3], d[4]),
            q           = decode_u16(d[5], d[6]) / 100.0,
            filter_type = FilterType(d[7]),
        )

    def get_all_bands(self) -> list[Band]:
        """Read all bands. Returns an empty list if band count is unknown."""
        count = self.get_band_count()
        if not count:
            return []
        bands: list[Band] = []
        for i in range(count):
            b = self.get_band(i)
            if b is not None:
                bands.append(b)
            time.sleep(self.inter_cmd_delay)
        return bands

    def get_preset_name(self, index: int) -> str | None:
        """Preset display name, or None if the device did not respond."""
        resp = self._get(CMD.PRESET_NAME, bytes([index]))
        p = parse_response(resp) if resp else None
        if not p or len(p[1]) < 2:
            return None
        return bytes(p[1][1:]).decode("utf-8", errors="replace").rstrip("\x00")

    # ─────────────────────────── SET API ───────────────────────────

    def set_eq_enabled(self, on: bool) -> None:
        self._set(CMD.EQ_SWITCH, bytes([1 if on else 0]))

    def set_user_slot(self, slot: int) -> None:
        """Switch to USER slot 1, 2, or 3.

        Equivalent to set_preset(160 + slot - 1) with validation against the
        Melody's three available USER slots.
        """
        if slot not in MELODY_USER_SLOTS:
            raise ValueError(
                f"Melody only has USER slots {MELODY_USER_SLOTS}, got {slot}."
            )
        self._set(CMD.EQ_PRESET, bytes([MELODY_PRESET_USER1 + slot - 1]))

    def set_preset(self, preset_id: int) -> None:
        """Switch preset by raw ID. USER1..USER3 = 160..162. Bypass = 240."""
        self._set(CMD.EQ_PRESET, bytes([preset_id & 0xFF]))

    def set_preamp(self, db: float) -> None:
        hi, lo = encode_gain(db)
        self._set(CMD.EQ_GAIN, bytes([hi, lo]))

    def set_band(
        self,
        index: int,
        freq: int,
        gain: float,
        q: float,
        filter_type: FilterType = FilterType.PEAK,
    ) -> None:
        """Set a single band. Not persisted until save_to_user()."""
        g_hi, g_lo = encode_gain(gain)
        f_hi, f_lo = encode_u16(freq)
        q_hi, q_lo = encode_u16(int(round(q * 100)))
        self._set(
            CMD.EQ_BAND,
            bytes([index, g_hi, g_lo, f_hi, f_lo, q_hi, q_lo, int(filter_type)]),
        )

    def set_bands(self, bands: list[Band]) -> None:
        for b in bands:
            self.set_band(b.index, b.freq, b.gain, b.q, b.filter_type)
            time.sleep(self.inter_cmd_delay)

    def save_to_user(self, slot: int) -> None:
        """Persist current EQ to USER slot 1, 2, or 3 so it survives reboot."""
        if slot not in MELODY_USER_SLOTS:
            raise ValueError(
                f"Melody only has USER slots {MELODY_USER_SLOTS}, got {slot}."
            )
        self._set(CMD.EQ_SAVE, bytes([slot]))

    def reset_eq(self) -> None:
        """Clear EQ on the currently selected slot."""
        self._set(CMD.EQ_RESET)
