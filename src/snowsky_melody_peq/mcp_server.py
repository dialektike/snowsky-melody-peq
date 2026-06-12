"""Optional MCP server exposing the Melody controller as Claude tools.

This module is gated by the ``mcp`` optional install:

    pip install snowsky-melody-peq[mcp]

It is loaded lazily — importing the rest of the library does not pull
in any MCP dependency. Run as::

    python -m snowsky_melody_peq.mcp_server     # via the module
    mcp-snowsky-melody                          # via the installed entry point

Every tool opens the device, performs its action, and closes
immediately. This makes it safe to alternate with the FiiO web UI
between calls — USB HID only allows one application to hold the device
at a time, so a long-lived hold by the MCP server would lock the user
out of the web.

Melody firmware quirks worth knowing when reading the tool docs (full
table in ``docs/PROTOCOL.md``):

- USER slot activation IDs are 7, 8, 9 (NOT the legacy 160..162).
- ``get_preset_state`` returns a "Personal / Modified" indicator, not
  the literal active slot ID.
- ``set_eq_enabled`` cannot be readback-verified; the recommended
  bypass path is ``set_preset(preset_id=240)``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import Band, FilterType, MelodyPEQ, parse_autoeq

mcp = FastMCP("snowsky-melody")


# ─── helpers ─────────────────────────────────────────────────

def _band_to_dict(b: Band) -> dict[str, Any]:
    return {
        "index":       b.index,
        "freq":        b.freq,
        "gain":        b.gain,
        "q":           b.q,
        "filter_type": b.filter_type.name,
    }


def _coerce_filter_type(value: str | int) -> FilterType:
    if isinstance(value, FilterType):
        return value
    if isinstance(value, int):
        return FilterType(value)
    return FilterType[value.upper()]


# Static factory-preset map (verified on hardware; see docs/PROTOCOL.md).
FACTORY_PRESETS: dict[int, str] = {
    0: "Jazz",
    1: "Pop",
    2: "Rock",
    3: "Dance",
    4: "R&B",
    5: "Classic",
    6: "Hip-Pop",
}


# ─── tools ───────────────────────────────────────────────────

@mcp.tool()
def get_state() -> dict[str, Any]:
    """Read the Melody's current EQ state.

    Returns the device name, the raw preset-indicator value, the global
    pre-amp in dB, the band count, and every PEQ band.

    ``preset_indicator`` is **not** a literal "current slot" query. It
    behaves as a Personal / Modified indicator (hardware-verified):

    - **0**: any programmatic ``set_*`` call via this server, or a
      live-EQ tweak in the web UI, leaves the indicator at 0. Says
      nothing about which slot is currently loaded.
    - **Non-zero**: the user just clicked that tile in the web UI and
      nothing has been modified since. The number is the activation ID
      — ``0..6`` factory presets (Jazz, Pop, Rock, Dance, R&B, Classic,
      Hip-Pop), ``7..9`` USER1..USER3, ``240`` bypass. In this case the
      value *does* match the active slot.

    Track the active slot in conversation state rather than relying on
    this field. The band content (``bands``) is always accurate.
    Canonical source: ``docs/PROTOCOL.md``.

    ``eq_enabled`` is always ``null`` on Melody — the device does not
    respond to the EQ_SWITCH query. Use ``set_preset(240)`` for bypass.
    """
    with MelodyPEQ() as d:
        return {
            "device":          d.name,
            "eq_enabled":      d.get_eq_enabled(),   # None on Melody
            "preset_indicator": d.get_preset(),       # Personal/Modified semantics
            "preamp_db":       d.get_preamp(),
            "band_count":      d.get_band_count(),
            "bands":           [_band_to_dict(b) for b in d.get_all_bands()],
        }


@mcp.tool()
def get_band(index: int) -> dict[str, Any] | None:
    """Read a single PEQ band by zero-based index."""
    with MelodyPEQ() as d:
        b = d.get_band(index)
    return _band_to_dict(b) if b else None


@mcp.tool()
def set_band(
    index: int,
    freq: int,
    gain: float,
    q: float,
    filter_type: str = "PEAK",
) -> dict[str, Any]:
    """Modify a single PEQ band on the live EQ.

    filter_type must be one of: PEAK, LOW_SHELF, HIGH_SHELF, BAND_PASS,
    LOW_PASS, HIGH_PASS, ALL_PASS. Range constraints (validated by the
    library): freq 20..20000 Hz, gain ±24 dB, Q 0.01..100.

    The change does NOT persist across reboot unless followed by
    `save_to_user`.
    """
    ft = _coerce_filter_type(filter_type)
    with MelodyPEQ() as d:
        d.set_band(index, freq=freq, gain=gain, q=q, filter_type=ft)
    return {"ok": True, "index": index, "freq": freq, "gain": gain, "q": q,
            "filter_type": ft.name}


@mcp.tool()
def set_preamp(db: float) -> dict[str, Any]:
    """Set the global pre-amp gain in dB (typically -24.0 .. +12.0)."""
    with MelodyPEQ() as d:
        d.set_preamp(db)
    return {"ok": True, "preamp_db": db}


@mcp.tool()
def set_preset(preset_id: int) -> dict[str, Any]:
    """Switch the active preset by raw activation ID.

    Valid Melody IDs: 0..6 (factory presets — see `list_factory_presets`),
    7..9 (USER1..USER3), 240 (explicit bypass; web UI's "Close EQ").
    Sending the legacy `160..162` makes the device drop to bypass.
    """
    if preset_id not in (*range(0, 10), 240):
        raise ValueError(
            f"preset_id must be in 0..9 or 240, got {preset_id}. "
            f"USER slots are 7/8/9, factory presets are 0..6, bypass is 240."
        )
    with MelodyPEQ() as d:
        d.set_preset(preset_id)
    return {"ok": True, "preset_id": preset_id}


@mcp.tool()
def set_user_slot(slot: int) -> dict[str, Any]:
    """Switch to USER1, USER2, or USER3 by slot number (1/2/3).

    The library translates to the right activation ID internally
    (slot 1 → preset 7, etc.).
    """
    with MelodyPEQ() as d:
        d.set_user_slot(slot)
    return {"ok": True, "slot": slot}


@mcp.tool()
def save_to_user(slot: int) -> dict[str, Any]:
    """**Destructive.** Persist the current live EQ to USER slot 1/2/3.

    This overwrites whatever was previously stored at that slot and
    survives USB power cycles (EEPROM-verified). Confirm with the user
    before invoking.
    """
    with MelodyPEQ() as d:
        d.save_to_user(slot)
    return {"ok": True, "slot": slot, "destructive": True}


@mcp.tool()
def reset_eq() -> dict[str, Any]:
    """**Destructive.** Flatten the currently active slot's EQ.

    All bands are zeroed on the currently selected slot. Confirm with
    the user before invoking.
    """
    with MelodyPEQ() as d:
        d.reset_eq()
    return {"ok": True, "destructive": True}


@mcp.tool()
def apply_autoeq(parametric_eq_text: str, slot: int = 1) -> dict[str, Any]:
    """**Destructive.** Apply an AutoEQ ``ParametricEQ.txt`` to a USER slot.

    Switches to the target USER slot, writes the parsed pre-amp and
    bands, pads any remaining device bands flat (0 dB) so the slot's
    previous EQ cannot bleed through underneath the new profile, then
    calls ``save_to_user(slot)`` so the result survives reboot.

    ``parametric_eq_text`` is always interpreted as the literal contents
    of a ParametricEQ.txt file from
    https://github.com/jaakkopasanen/AutoEq — never as a filesystem
    path. ``OFF`` filter lines are skipped and the remaining bands are
    re-indexed sequentially.

    Band-count truncation: if the source has more bands than the device
    exposes (the Melody has 10), the extra bands are dropped — typically
    the highest-frequency corrections. The return value carries enough
    information to detect this:

    Returns:
        ok:            always True if no exception was raised.
        slot:          the USER slot that was written (1, 2, or 3).
        preamp_db:     the pre-amp value applied.
        bands_parsed:  number of bands read from the input text.
        bands_written: number of bands actually applied to the device
                       (capped at the device's band count).
        truncated:     True if ``bands_parsed > bands_written``, i.e.
                       the bottom of the source profile was dropped.
                       Surface this to the user and suggest manually
                       trimming the source file when it matters.
        destructive:   marker that this tool overwrites a USER slot.
    """
    preamp, bands = parse_autoeq(parametric_eq_text)
    parsed_count = len(bands)
    with MelodyPEQ() as d:
        written_count, _device_count = d.apply_profile(preamp, bands, slot)
    return {
        "ok":            True,
        "slot":          slot,
        "preamp_db":     preamp,
        "bands_parsed":  parsed_count,
        "bands_written": written_count,
        "truncated":     parsed_count > written_count,
        "destructive":   True,
    }


@mcp.tool()
def get_user_slot_name(slot: int) -> dict[str, Any]:
    """Read the stored display name of USER slot 1/2/3.

    On Melody, slot names live at a different ID range than activation
    IDs; this tool handles that mapping internally.
    """
    with MelodyPEQ() as d:
        name = d.get_user_slot_name(slot)
    return {"slot": slot, "name": name}


@mcp.tool()
def list_factory_presets() -> dict[int, str]:
    """Static map of factory preset IDs to their names on the Melody."""
    return FACTORY_PRESETS


# ─── entry point ─────────────────────────────────────────────

def main() -> None:
    """Run the MCP server on stdio (the transport Claude Desktop uses)."""
    mcp.run()


if __name__ == "__main__":
    main()
