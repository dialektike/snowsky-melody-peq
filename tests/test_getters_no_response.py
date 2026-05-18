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


def test_get_user_slot_name_maps_to_name_lookup_id():
    """Slot 1/2/3 must query name-lookup IDs 160/161/162, not 7/8/9."""
    dev = _dev_with_no_response()
    seen: list[int] = []

    def fake_get_preset_name(index: int) -> str | None:
        seen.append(index)
        return None

    with patch.object(dev, "get_preset_name", side_effect=fake_get_preset_name):
        dev.get_user_slot_name(1)
        dev.get_user_slot_name(2)
        dev.get_user_slot_name(3)

    assert seen == [160, 161, 162]


def test_get_user_slot_name_rejects_invalid_slot():
    import pytest

    dev = _dev_with_no_response()
    with pytest.raises(ValueError, match="USER slots"):
        dev.get_user_slot_name(0)
    with pytest.raises(ValueError, match="USER slots"):
        dev.get_user_slot_name(4)
