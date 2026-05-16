"""Unit tests for the Melody identity check at open() time.

These tests mock hidapi so no real hardware is required.
"""

from unittest.mock import MagicMock, patch

import pytest

from snowsky_melody_peq import MelodyPEQ, MelodyPEQError, NotAMelodyError


def _hid_info(product: str | None, path: bytes = b"/dev/hidraw0") -> dict:
    """Build a hid.enumerate() result dict."""
    return {
        "vendor_id":      0x2972,
        "product_id":     0x0001,
        "path":           path,
        "product_string": product,
    }


def test_open_no_device_raises():
    with patch("snowsky_melody_peq.controller.hid.enumerate", return_value=[]):
        dev = MelodyPEQ()
        with pytest.raises(MelodyPEQError, match="No FiiO HID device"):
            dev.open()


def test_open_wrong_device_raises_not_a_melody():
    with patch("snowsky_melody_peq.controller.hid.enumerate",
               return_value=[_hid_info("FiiO K13 R2R")]):
        dev = MelodyPEQ()
        with pytest.raises(NotAMelodyError, match="not a SnowSky Melody"):
            dev.open()


def test_open_matches_case_insensitive():
    fake_hid = MagicMock()
    with patch("snowsky_melody_peq.controller.hid.enumerate",
               return_value=[_hid_info("SnowSky MELODY", b"/x")]), \
         patch("snowsky_melody_peq.controller.hid.device", return_value=fake_hid):
        dev = MelodyPEQ()
        dev.open()
        assert dev.name == "SnowSky MELODY"
        fake_hid.open_path.assert_called_once_with(b"/x")


def test_open_prefers_melody_among_multiple_devices():
    fake_hid = MagicMock()
    with patch("snowsky_melody_peq.controller.hid.enumerate",
               return_value=[
                   _hid_info("FiiO K13 R2R", b"/k13"),
                   _hid_info("SnowSky Melody", b"/melody"),
               ]), \
         patch("snowsky_melody_peq.controller.hid.device", return_value=fake_hid):
        dev = MelodyPEQ()
        dev.open()
        assert dev.name == "SnowSky Melody"
        fake_hid.open_path.assert_called_once_with(b"/melody")


def test_open_with_unnamed_device_raises():
    with patch("snowsky_melody_peq.controller.hid.enumerate",
               return_value=[_hid_info(None)]):
        dev = MelodyPEQ()
        with pytest.raises(NotAMelodyError):
            dev.open()


def test_open_failure_wraps_oserror():
    fake_hid = MagicMock()
    fake_hid.open_path.side_effect = OSError("Permission denied")
    with patch("snowsky_melody_peq.controller.hid.enumerate",
               return_value=[_hid_info("SnowSky Melody")]), \
         patch("snowsky_melody_peq.controller.hid.device", return_value=fake_hid):
        dev = MelodyPEQ()
        with pytest.raises(MelodyPEQError, match="Failed to open Melody"):
            dev.open()


def test_close_after_open_clears_state():
    fake_hid = MagicMock()
    with patch("snowsky_melody_peq.controller.hid.enumerate",
               return_value=[_hid_info("SnowSky Melody")]), \
         patch("snowsky_melody_peq.controller.hid.device", return_value=fake_hid):
        dev = MelodyPEQ()
        dev.open()
        assert dev.name == "SnowSky Melody"
        dev.close()
        assert dev.name == ""
        fake_hid.close.assert_called_once()


def test_save_to_user_validates_slot():
    dev = MelodyPEQ()
    with pytest.raises(ValueError, match="USER slots"):
        dev.save_to_user(slot=4)


def test_set_user_slot_validates():
    dev = MelodyPEQ()
    with pytest.raises(ValueError, match="USER slots"):
        dev.set_user_slot(0)
    with pytest.raises(ValueError, match="USER slots"):
        dev.set_user_slot(10)
