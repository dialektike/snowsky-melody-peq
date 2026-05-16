"""Unit tests for the protocol layer. These do not require a real device."""

from snowsky_melody_peq.protocol import (
    CMD, GET_HEAD, SET_HEAD, STOP, REPORT_ID, HID_REPORT_SIZE,
    build_get, build_set, wrap_hid_report, parse_response,
    encode_gain, decode_gain, encode_u16, decode_u16,
)


# ─── encoders ────────────────────────────────────────────

def test_encode_gain_roundtrip_positive():
    hi, lo = encode_gain(2.5)
    assert (hi, lo) == (0x00, 0x19)
    assert decode_gain(hi, lo) == 2.5

def test_encode_gain_roundtrip_negative():
    hi, lo = encode_gain(-2.5)
    assert (hi, lo) == (0xFF, 0xE7)
    assert decode_gain(hi, lo) == -2.5

def test_encode_gain_zero():
    assert encode_gain(0.0) == (0x00, 0x00)
    assert decode_gain(0, 0) == 0.0

def test_encode_u16_roundtrip():
    for v in [0, 1, 80, 2500, 20000, 0xFFFF]:
        hi, lo = encode_u16(v)
        assert decode_u16(hi, lo) == v


def test_encode_u16_rejects_overflow():
    import pytest
    with pytest.raises(ValueError, match="out of range"):
        encode_u16(0x10000)        # one past max
    with pytest.raises(ValueError, match="out of range"):
        encode_u16(-1)             # negative


def test_encode_gain_rejects_overflow():
    import pytest
    with pytest.raises(ValueError, match="i16 range"):
        encode_gain(4000.0)        # 40000 > 32767
    with pytest.raises(ValueError, match="i16 range"):
        encode_gain(-4000.0)


# ─── packet builders ─────────────────────────────────────

def test_build_get_minimal():
    pkt = build_get(CMD.EQ_COUNT)
    assert pkt == bytes([GET_HEAD, 0x0B, 0, 0, CMD.EQ_COUNT, 0, 0, STOP])

def test_build_set_with_data():
    pkt = build_set(CMD.EQ_SWITCH, bytes([0x01]))
    assert pkt == bytes([SET_HEAD, 0x0A, 0, 0, CMD.EQ_SWITCH, 1, 0x01, 0, STOP])

def test_build_set_band_payload_layout():
    # band 0, +4.0 dB, 80 Hz, Q=0.71, low-shelf (per PROTOCOL.md worked example)
    g_hi, g_lo = encode_gain(4.0)
    f_hi, f_lo = encode_u16(80)
    q_hi, q_lo = encode_u16(int(round(0.71 * 100)))
    data = bytes([0, g_hi, g_lo, f_hi, f_lo, q_hi, q_lo, 1])
    pkt  = build_set(CMD.EQ_BAND, data)
    assert pkt == bytes([
        SET_HEAD, 0x0A, 0, 0, CMD.EQ_BAND, 8,
        0x00, 0x00, 0x28, 0x00, 0x50, 0x00, 0x47, 0x01,
        0x00, STOP,
    ])


# ─── HID report wrapper ──────────────────────────────────

def test_wrap_hid_report_size_and_prefix():
    pkt = build_get(CMD.EQ_COUNT)
    report = wrap_hid_report(pkt)
    assert len(report) == HID_REPORT_SIZE
    assert report[0] == REPORT_ID
    assert report[1:1 + len(pkt)] == pkt
    assert all(b == 0 for b in report[1 + len(pkt):])


# ─── response parser ─────────────────────────────────────

def test_parse_response_strips_report_id_and_extracts_data():
    raw = bytes([REPORT_ID, GET_HEAD, 0x0B, 0, 0, CMD.EQ_COUNT, 1, 5, 0, STOP])
    parsed = parse_response(raw)
    assert parsed == (CMD.EQ_COUNT, bytes([5]))

def test_parse_response_handles_data_without_report_id():
    """Some hidapi platforms strip the Report ID byte before delivering."""
    raw = bytes([GET_HEAD, 0x0B, 0, 0, CMD.EQ_COUNT, 1, 5, 0, STOP])
    parsed = parse_response(raw)
    assert parsed == (CMD.EQ_COUNT, bytes([5]))

def test_parse_response_rejects_truncated():
    assert parse_response(b"") is None
    assert parse_response(bytes([REPORT_ID, GET_HEAD])) is None

def test_parse_response_handles_band_payload():
    payload = bytes([0, 0x00, 0x28, 0x00, 0x50, 0x00, 0x47, 0x01])
    raw = bytes([REPORT_ID, GET_HEAD, 0x0B, 0, 0, CMD.EQ_BAND, 8]) + payload + bytes([0, STOP])
    parsed = parse_response(raw)
    assert parsed is not None
    cmd, data = parsed
    assert cmd == CMD.EQ_BAND
    assert data == payload
