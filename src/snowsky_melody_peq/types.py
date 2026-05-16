"""Public data types for fiio-peq."""

from __future__ import annotations
from dataclasses import dataclass
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
        gain:  Gain in dB. Resolution: 0.1 dB.
        q:     Q factor. Resolution: 0.01.
        filter_type: Biquad filter shape.
    """
    index: int
    freq: int
    gain: float
    q: float
    filter_type: FilterType = FilterType.PEAK

    def __str__(self) -> str:
        return (f"Band {self.index}: {self.freq}Hz {self.gain:+.1f}dB "
                f"Q={self.q:.2f} {self.filter_type.name}")
