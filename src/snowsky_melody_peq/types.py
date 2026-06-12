"""Public data types for snowsky-melody-peq."""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from enum import IntEnum


class FilterType(IntEnum):
    """Biquad filter shape. Values match FiiO USB HID protocol byte."""
    PEAK       = 0
    LOW_SHELF  = 1
    HIGH_SHELF = 2
    BAND_PASS  = 3
    LOW_PASS   = 4
    HIGH_PASS  = 5
    ALL_PASS   = 6


@dataclass
class Band:
    """Single PEQ band.

    Attributes:
        index: Zero-based band slot on the device.
        freq:  Center / corner frequency in Hz (20..20000).
        gain:  Gain in dB (-24.0..+24.0). Resolution: 0.1 dB.
        q:     Q factor (0.01..100.0). Resolution: 0.01.
        filter_type: Biquad filter shape.
        validate: Init-only flag. ``True`` (default) applies the range
            checks below — use this for every band that is *going to* the
            device. ``False`` skips them — use this only when constructing
            a Band from values *reported by* the device, which may legally
            sit outside the write-side ranges (e.g. ``freq=0`` on a
            factory-fresh or reset band) and must be surfaced to the
            caller rather than raise.

    Range checks fire in ``__post_init__`` so that nonsensical values are
    rejected at the Python layer rather than silently wrapping in the
    16-bit on-wire encoding (see ``protocol.encode_u16``).
    """
    index: int
    freq: int
    gain: float
    q: float
    filter_type: FilterType = FilterType.PEAK
    validate: InitVar[bool] = True

    def __post_init__(self, validate: bool) -> None:
        if not isinstance(self.filter_type, FilterType):
            self.filter_type = FilterType(self.filter_type)
        if not validate:
            return
        if self.index < 0:
            raise ValueError(f"Band index must be >= 0, got {self.index}")
        if not 20 <= self.freq <= 20000:
            raise ValueError(f"freq {self.freq} Hz out of range 20..20000")
        if not -24.0 <= self.gain <= 24.0:
            raise ValueError(f"gain {self.gain} dB out of range -24.0..+24.0")
        if not 0.01 <= self.q <= 100.0:
            raise ValueError(f"Q {self.q} out of range 0.01..100.0")

    def __str__(self) -> str:
        return (f"Band {self.index}: {self.freq}Hz {self.gain:+.1f}dB "
                f"Q={self.q:.2f} {self.filter_type.name}")
