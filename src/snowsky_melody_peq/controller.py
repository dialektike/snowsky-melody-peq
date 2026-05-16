"""SnowSky Melody PEQ device controller.

This controller is intentionally locked to the SnowSky Melody. On open, it
verifies that the connected USB device identifies itself as a Melody, and
refuses to talk to anything else. This is a safety choice: although other
FiiO devices share the USB HID EQ protocol, only the Melody has been
designated as in-scope for this library.
"""

from __future__ import annotations
import time
import usb.core
import usb.util

from .protocol import (
    VENDOR_ID, INTERFACE, EP_OUT, EP_IN, HID_REPORT_SIZE, TIMEOUT_MS,
    CMD, build_get, build_set, wrap_hid_report, parse_response,
    encode_gain, decode_gain, encode_u16, decode_u16,
)
from .types import Band, FilterType


# ─── Melody identity ──────────────────────────────────────────
# The USB product string is matched case-insensitively as a substring.
# Add to this tuple if FiiO ships the Melody with a slightly different
# product string (e.g. firmware variants, regional SKUs).
MELODY_PRODUCT_KEYWORDS: tuple[str, ...] = ("melody",)

# Known Melody capabilities. These are the most likely values based on the
# device's documented PEQ UI; the library still queries the actual band count
# from the device at runtime via get_band_count() before any batch write.
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
    """USB HID controller for the FiiO SnowSky Melody.

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
        No FiiO device found, or the device cannot be claimed.
    NotAMelodyError
        A FiiO device was found, but its product string did not identify it
        as a SnowSky Melody.
    """

    def __init__(self, inter_cmd_delay: float = 0.03):
        self.inter_cmd_delay = inter_cmd_delay
        self._dev: usb.core.Device | None = None
        self._kernel_was_attached = False

    # ── context manager ──
    def __enter__(self) -> "MelodyPEQ":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ── connection lifecycle ──
    def open(self) -> None:
        candidates = list(usb.core.find(idVendor=VENDOR_ID, find_all=True) or [])
        if not candidates:
            raise MelodyPEQError(
                f"No FiiO device found (VID=0x{VENDOR_ID:04X}). "
                f"Check that the Melody is connected and powered."
            )

        melody = next(
            (
                dev for dev in candidates
                if any(kw in (dev.product or "").lower()
                       for kw in MELODY_PRODUCT_KEYWORDS)
            ),
            None,
        )
        if melody is None:
            names = [dev.product or "<unnamed>" for dev in candidates]
            raise NotAMelodyError(
                f"Connected FiiO device(s) are not a SnowSky Melody: {names}. "
                f"This library only supports the Melody."
            )

        self._dev = melody
        if self._dev.is_kernel_driver_active(INTERFACE):
            self._dev.detach_kernel_driver(INTERFACE)
            self._kernel_was_attached = True
        usb.util.claim_interface(self._dev, INTERFACE)

    def close(self) -> None:
        if not self._dev:
            return
        try:
            usb.util.release_interface(self._dev, INTERFACE)
            if self._kernel_was_attached:
                self._dev.attach_kernel_driver(INTERFACE)
        except Exception:
            pass
        self._dev = None
        self._kernel_was_attached = False

    @property
    def name(self) -> str:
        return self._dev.product if self._dev else ""

    # ── low-level transport ──
    def _drain(self) -> None:
        try:
            while True:
                self._dev.read(EP_IN, HID_REPORT_SIZE, timeout=30)
        except (usb.core.USBTimeoutError, usb.core.USBError):
            pass

    def _exchange(self, packet: bytes, expect_cmd: int) -> bytes | None:
        if self._dev is None:
            raise MelodyPEQError("Device not open. Call .open() or use 'with'.")
        self._drain()
        self._dev.write(EP_OUT, wrap_hid_report(packet), timeout=500)
        for _ in range(2):
            try:
                raw = bytes(self._dev.read(EP_IN, HID_REPORT_SIZE, timeout=TIMEOUT_MS))
            except usb.core.USBTimeoutError:
                return None
            parsed = parse_response(raw)
            if parsed and parsed[0] == expect_cmd:
                return raw
        return None

    def _get(self, cmd: int, data: bytes = b"") -> bytes | None:
        return self._exchange(build_get(cmd, data), cmd)

    def _set(self, cmd: int, data: bytes = b"") -> bytes | None:
        return self._exchange(build_set(cmd, data), cmd)

    # ─────────────────────────── GET API ───────────────────────────

    def get_band_count(self) -> int:
        """Number of PEQ bands the Melody supports.

        Queried from the device rather than assumed, since firmware updates
        may change this.
        """
        resp = self._get(CMD.EQ_COUNT)
        p = parse_response(resp) if resp else None
        return p[1][0] if p and p[1] else 0

    def get_eq_enabled(self) -> bool:
        resp = self._get(CMD.EQ_SWITCH)
        p = parse_response(resp) if resp else None
        return bool(p[1][0]) if p and p[1] else False

    def get_preset(self) -> int:
        """Current preset ID. 160-162 = USER1..USER3, 240 = bypass."""
        resp = self._get(CMD.EQ_PRESET)
        p = parse_response(resp) if resp else None
        return p[1][0] if p and p[1] else -1

    def get_preamp(self) -> float:
        """Global pre-amp gain in dB."""
        resp = self._get(CMD.EQ_GAIN)
        p = parse_response(resp) if resp else None
        return decode_gain(p[1][0], p[1][1]) if p and len(p[1]) >= 2 else 0.0

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
        bands: list[Band] = []
        for i in range(self.get_band_count()):
            b = self.get_band(i)
            if b is not None:
                bands.append(b)
            time.sleep(self.inter_cmd_delay)
        return bands

    def get_preset_name(self, index: int) -> str:
        resp = self._get(CMD.PRESET_NAME, bytes([index]))
        p = parse_response(resp) if resp else None
        if not p or len(p[1]) < 2:
            return ""
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
