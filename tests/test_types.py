"""Unit tests for Band validation in types.py."""

import pytest

from snowsky_melody_peq import Band, FilterType


def test_band_accepts_valid_values():
    b = Band(index=0, freq=1000, gain=-3.0, q=1.0, filter_type=FilterType.PEAK)
    assert b.freq == 1000
    assert b.filter_type is FilterType.PEAK


def test_band_rejects_negative_index():
    with pytest.raises(ValueError, match="index"):
        Band(index=-1, freq=1000, gain=0.0, q=1.0)


def test_band_rejects_freq_out_of_range():
    with pytest.raises(ValueError, match="freq"):
        Band(index=0, freq=0, gain=0.0, q=1.0)
    with pytest.raises(ValueError, match="freq"):
        Band(index=0, freq=30000, gain=0.0, q=1.0)


def test_band_rejects_gain_out_of_range():
    with pytest.raises(ValueError, match="gain"):
        Band(index=0, freq=1000, gain=30.0, q=1.0)
    with pytest.raises(ValueError, match="gain"):
        Band(index=0, freq=1000, gain=-30.0, q=1.0)


def test_band_rejects_q_out_of_range():
    """Catches the silent encode_u16 wrap at Q > 655.35."""
    with pytest.raises(ValueError, match="Q"):
        Band(index=0, freq=1000, gain=0.0, q=0.0)
    with pytest.raises(ValueError, match="Q"):
        Band(index=0, freq=1000, gain=0.0, q=200.0)


def test_band_coerces_int_filter_type():
    b = Band(index=0, freq=1000, gain=0.0, q=1.0, filter_type=1)  # type: ignore[arg-type]
    assert b.filter_type is FilterType.LOW_SHELF


def test_band_rejects_invalid_filter_type_int():
    with pytest.raises(ValueError):
        Band(index=0, freq=1000, gain=0.0, q=1.0, filter_type=99)  # type: ignore[arg-type]
