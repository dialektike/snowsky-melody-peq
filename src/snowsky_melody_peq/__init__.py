"""snowsky-melody-peq: USB HID PEQ control for the FiiO SnowSky Melody.

A Python library and CLI for setting parametric-EQ on the SnowSky Melody DAC
without the FiiO Control Android app or web interface.

This is a Melody-only library. It refuses to operate on any other USB device,
including other FiiO models with a similar protocol.

Protocol reverse engineering source: SmookeyDev/fiio-k13-control (MIT).

Example:
    >>> from snowsky_melody_peq import MelodyPEQ, Band, FilterType
    >>> with MelodyPEQ() as dev:
    ...     for band in dev.get_all_bands():
    ...         print(band)
    ...     dev.set_band(0, freq=80, gain=-3.5, q=0.71,
    ...                  filter_type=FilterType.LOW_SHELF)
    ...     dev.save_to_user(slot=1)
"""

from .autoeq import parse_autoeq, parse_autoeq_file
from .controller import MelodyPEQ, MelodyPEQError, NotAMelodyError
from .types import Band, FilterType

__version__ = "0.1.0"
__all__ = [
    "MelodyPEQ",
    "MelodyPEQError",
    "NotAMelodyError",
    "Band",
    "FilterType",
    "parse_autoeq",
    "parse_autoeq_file",
    "__version__",
]
