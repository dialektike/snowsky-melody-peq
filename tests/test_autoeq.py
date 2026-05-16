"""Unit tests for the AutoEQ parser."""

from snowsky_melody_peq import FilterType, parse_autoeq

SAMPLE = """\
GraphicEQ: 20 -3.5; 21 -3.4; 22 -3.4
Preamp: -6.5 dB
Filter 1: ON PK Fc 105 Hz Gain -4.0 dB Q 0.75
Filter 2: ON LSC Fc 35 Hz Gain +3.0 dB Q 0.71
Filter 3: ON HSC Fc 10000 Hz Gain -2.0 dB Q 0.71
Filter 4: OFF PK Fc 5000 Hz Gain 0.0 dB Q 1.0
"""


def test_parse_autoeq_preamp_and_count():
    preamp, bands = parse_autoeq(SAMPLE)
    assert preamp == -6.5
    # filter 4 is OFF and is skipped
    assert len(bands) == 3


def test_parse_autoeq_band_values():
    _, bands = parse_autoeq(SAMPLE)
    by_idx = {b.index: b for b in bands}

    assert by_idx[0].freq == 105
    assert by_idx[0].gain == -4.0
    assert by_idx[0].q == 0.75
    assert by_idx[0].filter_type is FilterType.PEAK

    assert by_idx[1].filter_type is FilterType.LOW_SHELF
    assert by_idx[2].filter_type is FilterType.HIGH_SHELF
    assert by_idx[2].freq == 10000


def test_parse_autoeq_empty_string():
    preamp, bands = parse_autoeq("")
    assert preamp == 0.0
    assert bands == []


def test_parse_autoeq_no_preamp_line():
    text = "Filter 1: ON PK Fc 1000 Hz Gain +1.0 dB Q 1.0"
    preamp, bands = parse_autoeq(text)
    assert preamp == 0.0
    assert len(bands) == 1
