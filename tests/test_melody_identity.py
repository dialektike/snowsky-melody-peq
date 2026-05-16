"""Unit tests for the Melody identity check at open() time.

These tests mock pyusb so no real hardware is required.
"""

from unittest.mock import patch

import pytest

from snowsky_melody_peq import MelodyPEQ, MelodyPEQError, NotAMelodyError


class _FakeDevice:
    """Minimal stand-in for usb.core.Device used by the controller."""

    def __init__(self, product: str | None):
        self.product = product

    # Methods the controller invokes after identity check; we no-op them.
    def is_kernel_driver_active(self, _iface):  # noqa: D401
        return False

    def detach_kernel_driver(self, _iface):
        pass

    def attach_kernel_driver(self, _iface):
        pass


def test_open_no_device_raises():
    with patch("snowsky_melody_peq.controller.usb.core.find", return_value=[]):
        dev = MelodyPEQ()
        with pytest.raises(MelodyPEQError, match="No FiiO device"):
            dev.open()


def test_open_wrong_device_raises_not_a_melody():
    fake = _FakeDevice(product="FiiO K13 R2R")
    with patch("snowsky_melody_peq.controller.usb.core.find", return_value=[fake]):
        dev = MelodyPEQ()
        with pytest.raises(NotAMelodyError, match="not a SnowSky Melody"):
            dev.open()


def test_open_matches_case_insensitive():
    fake = _FakeDevice(product="SnowSky MELODY")
    with patch("snowsky_melody_peq.controller.usb.core.find", return_value=[fake]), \
         patch("snowsky_melody_peq.controller.usb.util.claim_interface"):
        dev = MelodyPEQ()
        dev.open()
        assert dev.name == "SnowSky MELODY"


def test_open_prefers_melody_among_multiple_devices():
    not_melody = _FakeDevice(product="FiiO K13 R2R")
    melody     = _FakeDevice(product="SnowSky Melody")
    with patch("snowsky_melody_peq.controller.usb.core.find",
               return_value=[not_melody, melody]), \
         patch("snowsky_melody_peq.controller.usb.util.claim_interface"):
        dev = MelodyPEQ()
        dev.open()
        assert dev.name == "SnowSky Melody"


def test_open_with_unnamed_device_raises():
    fake = _FakeDevice(product=None)
    with patch("snowsky_melody_peq.controller.usb.core.find", return_value=[fake]):
        dev = MelodyPEQ()
        with pytest.raises(NotAMelodyError):
            dev.open()


def test_save_to_user_validates_slot():
    dev = MelodyPEQ()
    with pytest.raises(ValueError, match="USER slots"):
        dev.save_to_user(slot=4)  # Melody only has 1-3


def test_set_user_slot_validates():
    dev = MelodyPEQ()
    with pytest.raises(ValueError, match="USER slots"):
        dev.set_user_slot(0)
    with pytest.raises(ValueError, match="USER slots"):
        dev.set_user_slot(10)
