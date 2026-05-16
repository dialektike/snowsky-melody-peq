"""Verify getters return None when the device does not answer.

This protects against the silent-False bug where missing responses were
indistinguishable from a real ``EQ off`` / ``0 bands`` / etc. reading.
The Melody is known to ignore CMD.EQ_SWITCH (0x1A), so its absence of a
response must surface to the caller as ``None`` rather than ``False``.
"""

from unittest.mock import patch

from snowsky_melody_peq import MelodyPEQ


def _dev_with_no_response() -> MelodyPEQ:
    dev = MelodyPEQ()
    # bypass open(): plug in a sentinel so _exchange's "device not open"
    # guard is satisfied, then make _exchange always report "no response".
    dev._dev = object()
    return dev


def test_get_eq_enabled_returns_none_on_no_response():
    dev = _dev_with_no_response()
    with patch.object(dev, "_exchange", return_value=None):
        assert dev.get_eq_enabled() is None


def test_get_band_count_returns_none_on_no_response():
    dev = _dev_with_no_response()
    with patch.object(dev, "_exchange", return_value=None):
        assert dev.get_band_count() is None


def test_get_preset_returns_none_on_no_response():
    dev = _dev_with_no_response()
    with patch.object(dev, "_exchange", return_value=None):
        assert dev.get_preset() is None


def test_get_preamp_returns_none_on_no_response():
    dev = _dev_with_no_response()
    with patch.object(dev, "_exchange", return_value=None):
        assert dev.get_preamp() is None


def test_get_preset_name_returns_none_on_no_response():
    dev = _dev_with_no_response()
    with patch.object(dev, "_exchange", return_value=None):
        assert dev.get_preset_name(0) is None


def test_get_all_bands_returns_empty_when_count_unknown():
    dev = _dev_with_no_response()
    with patch.object(dev, "_exchange", return_value=None):
        assert dev.get_all_bands() == []
