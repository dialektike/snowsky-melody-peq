"""Parser for AutoEQ ``ParametricEQ.txt`` files.

AutoEQ (https://github.com/jaakkopasanen/AutoEq) publishes per-headphone PEQ
profiles in a standard text format:

    Preamp: -6.5 dB
    Filter 1: ON PK Fc 105 Hz Gain -4.0 dB Q 0.75
    Filter 2: ON LSC Fc 35 Hz Gain +3.0 dB Q 0.71
    Filter 3: ON HSC Fc 10000 Hz Gain -2.0 dB Q 0.71
    ...

This module parses such files into the ``Band`` data type used by
``snowsky_melody_peq``.

Two entry points:

- :func:`parse_autoeq` — parses *content*. A ``str`` argument is always
  treated as the text itself, never as a path. (Earlier versions guessed
  path-vs-content from the string shape; a mistyped path then silently
  parsed as empty content, and a hostile single-line string could read an
  arbitrary local file. Both failure modes are gone.)
- :func:`parse_autoeq_file` — parses a *file* and raises the usual
  ``FileNotFoundError`` / ``OSError`` if it cannot be read.
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
    """Parse AutoEQ ParametricEQ content.

    Parameters
    ----------
    source : str | Path
        ``str``  — the file *contents* (never interpreted as a path).
        ``Path`` — a file to read.

    Returns
    -------
    preamp : float
        Pre-amp gain in dB (0.0 if not specified).
    bands : list[Band]
        Parsed filter bands. Lines marked ``OFF`` are skipped, and the
        surviving bands are re-indexed sequentially from 0 — the ``Filter
        N`` numbers in the source are *not* used as device indices, so an
        OFF line in the middle of a profile cannot leave a gap that would
        preserve stale EQ on the device.
    """
    text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source

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
                index       = len(bands),  # sequential, gap-free
                filter_type = _FILTER_TYPE_MAP.get(m.group(2).upper(), FilterType.PEAK),
                freq        = int(float(m.group(3))),
                gain        = float(m.group(4)),
                q           = float(m.group(5)),
            ))

    return preamp, bands


def parse_autoeq_file(path: str | Path) -> tuple[float, list[Band]]:
    """Parse an AutoEQ ParametricEQ.txt *file*.

    Unlike passing a ``str`` to :func:`parse_autoeq`, this raises
    ``FileNotFoundError`` (or any other ``OSError``) if the file cannot
    be read, so a mistyped path fails loudly instead of yielding an
    empty profile.
    """
    return parse_autoeq(Path(path).read_text(encoding="utf-8"))
