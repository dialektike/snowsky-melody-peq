"""Regression tests for the validation / apply-semantics fixes.

Covers four previously confirmed bugs:

1. ``MelodyPEQ.set_band()`` bypassed ``Band``'s range validation, so
   out-of-range values (e.g. freq=5, gain=30) went straight to the wire.
2. ``parse_autoeq()`` guessed path-vs-content from the string shape, so a
   mistyped path silently parsed as an empty profile (and a single-line
   string matching an existing file would read that file).
3. AutoEQ ``OFF`` filters left gaps in band indices, and short profiles
   left the device's higher bands untouched — stale EQ from the slot's
   previous contents survived an "apply".
4. ``get_band()`` applied write-side range validation to device-reported
   values, raising ValueError on e.g. ``freq=0`` from a reset band.
"""

from unittest.mock import patch

import pytest

from snowsky_melody_peq import (
    Band,
    FilterType,
    MelodyPEQ,
    parse_autoeq,
    parse_autoeq_file,
)
from snowsky_melody_peq.protocol import CMD, GET_HEAD, REPORT_ID, STOP


def _dev() -> MelodyPEQ:
    d = MelodyPEQ(inter_cmd_delay=0.0)
    d._dev = object()  # satisfy the "device not open" guard
    return d


# ─── 1. set_band validates ────────────────────────────────────

def test_set_band_rejects_out_of_range_freq():
    dev = _dev()
    with patch.object(dev, "_exchange") as ex:
        with pytest.raises(ValueError, match="freq"):
            dev.set_band(0, freq=5, gain=0.0, q=1.0)
        ex.assert_not_called()


def test_set_band_rejects_out_of_range_gain():
    dev = _dev()
    with patch.object(dev, "_exchange") as ex:
        with pytest.raises(ValueError, match="gain"):
            dev.set_band(0, freq=1000, gain=30.0, q=1.0)
        ex.assert_not_called()


def test_set_band_rejects_out_of_range_q():
    dev = _dev()
    with patch.object(dev, "_exchange") as ex:
        with pytest.raises(ValueError, match="Q"):
            dev.set_band(0, freq=1000, gain=0.0, q=0.005)
        ex.assert_not_called()


def test_set_band_in_range_still_writes():
    dev = _dev()
    with patch.object(dev, "_exchange", return_value=None) as ex:
        dev.set_band(0, freq=80, gain=4.0, q=0.71,
                     filter_type=FilterType.LOW_SHELF)
        ex.assert_called_once()


# ─── 2. parse_autoeq str = content; file errors are loud ──────

def test_parse_autoeq_str_is_always_content():
    # A path-looking single-line string is parsed as (empty) content,
    # never opened as a file.
    preamp, bands = parse_autoeq("HE-X4_ParametricEQ.txt")
    assert (preamp, bands) == (0.0, [])


def test_parse_autoeq_file_raises_on_missing_path():
    with pytest.raises(FileNotFoundError):
        parse_autoeq_file("definitely_missing_ParametricEQ.txt")


def test_parse_autoeq_file_reads_real_file(tmp_path):
    f = tmp_path / "ParametricEQ.txt"
    f.write_text("Preamp: -3.0 dB\n"
                 "Filter 1: ON PK Fc 100 Hz Gain -2.0 dB Q 1.0\n")
    preamp, bands = parse_autoeq_file(f)
    assert preamp == -3.0
    assert len(bands) == 1


# ─── 3. gap-free indices + flat padding on apply ──────────────

OFF_GAP_SAMPLE = """\
Preamp: -3.0 dB
Filter 1: ON PK Fc 100 Hz Gain -2.0 dB Q 1.0
Filter 2: OFF PK Fc 500 Hz Gain 0.0 dB Q 1.0
Filter 3: ON PK Fc 2000 Hz Gain -1.0 dB Q 1.0
"""


def test_parse_autoeq_reindexes_after_off_filter():
    _, bands = parse_autoeq(OFF_GAP_SAMPLE)
    assert [b.index for b in bands] == [0, 1]
    assert bands[1].freq == 2000  # Filter 3's content at index 1


def test_apply_profile_pads_remaining_bands_flat():
    dev = _dev()
    written_bands: list[Band] = []
    with patch.object(dev, "get_band_count", return_value=10), \
         patch.object(dev, "set_user_slot"), \
         patch.object(dev, "set_preamp"), \
         patch.object(dev, "save_to_user"), \
         patch.object(dev, "set_bands", side_effect=written_bands.extend):
        _, bands = parse_autoeq(OFF_GAP_SAMPLE)
        written, count = dev.apply_profile(-3.0, bands, slot=1)

    assert (written, count) == (2, 10)
    assert len(written_bands) == 10
    assert [b.index for b in written_bands] == list(range(10))
    # bands 2..9 are flat: stale slot EQ cannot bleed through
    assert all(b.gain == 0.0 for b in written_bands[2:])
    # the real profile content is intact
    assert written_bands[0].freq == 100 and written_bands[0].gain == -2.0
    assert written_bands[1].freq == 2000 and written_bands[1].gain == -1.0


def test_apply_profile_truncates_and_reports():
    dev = _dev()
    bands = [Band(index=i, freq=100 + i, gain=-1.0, q=1.0) for i in range(12)]
    captured: list[Band] = []
    with patch.object(dev, "get_band_count", return_value=10), \
         patch.object(dev, "set_user_slot"), \
         patch.object(dev, "set_preamp"), \
         patch.object(dev, "save_to_user"), \
         patch.object(dev, "set_bands", side_effect=captured.extend):
        written, count = dev.apply_profile(0.0, bands, slot=2)

    assert (written, count) == (10, 10)
    assert len(captured) == 10


def test_apply_profile_refuses_without_band_count():
    from snowsky_melody_peq import MelodyPEQError

    dev = _dev()
    with patch.object(dev, "get_band_count", return_value=None):
        with pytest.raises(MelodyPEQError, match="band count"):
            dev.apply_profile(0.0, [], slot=1)


# ─── 4. get_band never raises on device-reported values ───────

def _band_response(index: int, gain_raw: int, freq: int, q_raw: int,
                   ftype: int) -> bytes:
    payload = bytes([
        index,
        (gain_raw >> 8) & 0xFF, gain_raw & 0xFF,
        (freq >> 8) & 0xFF, freq & 0xFF,
        (q_raw >> 8) & 0xFF, q_raw & 0xFF,
        ftype,
    ])
    return (bytes([REPORT_ID, GET_HEAD, 0x0B, 0, 0, CMD.EQ_BAND, len(payload)])
            + payload + bytes([0, STOP]))


def test_get_band_accepts_out_of_range_device_values():
    dev = _dev()
    # freq=0, q=0.00 — legal on a factory-fresh/reset band, but outside
    # the write-side ranges. Must be reported, not raised.
    raw = _band_response(index=0, gain_raw=0, freq=0, q_raw=0, ftype=0)
    with patch.object(dev, "_exchange", return_value=raw):
        b = dev.get_band(0)
    assert b is not None
    assert b.freq == 0
    assert b.q == 0.0
    assert b.filter_type is FilterType.PEAK


def test_band_validate_false_skips_range_checks():
    b = Band(index=0, freq=0, gain=0.0, q=0.0, validate=False)
    assert b.freq == 0
    with pytest.raises(ValueError):
        Band(index=0, freq=0, gain=0.0, q=0.0)  # default validates
