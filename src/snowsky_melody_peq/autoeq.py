"""Parser for AutoEQ ``ParametricEQ.txt`` files.

AutoEQ (https://github.com/jaakkopasanen/AutoEq) publishes per-headphone PEQ
profiles in a standard text format:

    Preamp: -6.5 dB
    Filter 1: ON PK Fc 105 Hz Gain -4.0 dB Q 0.75
    Filter 2: ON LSC Fc 35 Hz Gain +3.0 dB Q 0.71
    Filter 3: ON HSC Fc 10000 Hz Gain -2.0 dB Q 0.71
    ...

This module parses such files into the ``Band`` data type used by ``fiio_peq``.
"""

from __future__ import annotations
import re
from pathlib import Path

from .types import Band, FilterType

_FILTER_TYPE_MAP: dict[str, FilterType] = {
    "PK":  FilterType.PEAK,
    "LSC": FilterType.LOW_SHELF,
    "HSC": FilterType.HIGH_SHELF,
    "LS":  FilterType.LOW_SHELF,
    "HS":  FilterType.HIGH_SHELF,
    "BP":  FilterType.BAND_PASS,
    "LP":  FilterType.LOW_PASS,
    "HP":  FilterType.HIGH_PASS,
    "AP":  FilterType.ALL_PASS,
}

_PREAMP_RE = re.compile(r"^Preamp:\s*([-+]?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)
_FILTER_RE = re.compile(
    r"^Filter\s+(\d+):\s*ON\s+(\w+)\s+Fc\s+(\d+(?:\.\d+)?)\s*Hz\s+"
    r"Gain\s+([-+]?\d+(?:\.\d+)?)\s*dB\s+Q\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def parse_autoeq(source: str | Path) -> tuple[float, list[Band]]:
    """Parse an AutoEQ ParametricEQ.txt file or string.

    Parameters
    ----------
    source : str | Path
        Either a path to a file, or the file contents as a string.

    Returns
    -------
    preamp : float
        Pre-amp gain in dB (0.0 if not specified).
    bands : list[Band]
        Parsed filter bands. Indices are zero-based and reflect the order
        in the source file. Lines marked ``OFF`` are skipped.
    """
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    elif isinstance(source, str) and source and "\n" not in source:
        p = Path(source)
        text = p.read_text(encoding="utf-8") if p.is_file() else source
    else:
        text = str(source)

    preamp = 0.0
    bands: list[Band] = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if m := _PREAMP_RE.match(line):
            preamp = float(m.group(1))
        elif m := _FILTER_RE.match(line):
            bands.append(Band(
                index       = int(m.group(1)) - 1,  # convert to zero-based
                filter_type = _FILTER_TYPE_MAP.get(m.group(2).upper(), FilterType.PEAK),
                freq        = int(float(m.group(3))),
                gain        = float(m.group(4)),
                q           = float(m.group(5)),
            ))

    return preamp, bands
