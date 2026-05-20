# MCP tool reference

Signatures and Melody-specific behaviour for every tool exposed by the optional MCP server (`snowsky_melody_peq.mcp_server`). Install the extra to enable it:

```bash
pip install snowsky-melody-peq[mcp]
```

Then register the `mcp-snowsky-melody` console script with your MCP client (see [`../README.md`](../README.md) for Claude Desktop / Claude Code config snippets).

The underlying behaviour comes from the core library in this same repository; this document only summarises it from the MCP client's perspective. For protocol-level detail see [`PROTOCOL.md`](PROTOCOL.md).

## Read

### `get_state() -> dict`

Reads the device's current EQ state. Returned dict:

| Field | Type | Notes |
|---|---|---|
| `device` | str | The HID product string (typically `"SNOWSKY Melody"`) |
| `eq_enabled` | bool \| null | **Always `null` on Melody** — the device does not respond to `EQ_SWITCH` GET |
| `preset_indicator` | int \| null | A "Personal / Modified" indicator, **not** a current-slot query. See note below |
| `preamp_db` | float \| null | Global pre-amp in dB |
| `band_count` | int \| null | Number of PEQ bands (10 on Melody) |
| `bands` | list[Band] | One entry per band with `index`, `freq`, `gain`, `q`, `filter_type` |

`preset_indicator` is a "Personal / Modified" indicator on Melody, not a "current slot" query — full per-scenario table in [`PROTOCOL.md`](PROTOCOL.md#dual-preset-id-scheme-verified-on-hardware). The band content (`bands` field) is always accurate regardless.

### `get_band(index: int) -> dict | null`

A single band at the given zero-based index, or `null` if the device did not return that band.

### `get_user_slot_name(slot: int) -> {slot, name}`

Stored display name of USER slot `slot` (1/2/3), e.g. `"HIFIMAN"`, `"FT5"`. Returns `null` for `name` if the device did not respond.

### `list_factory_presets() -> {int: str}`

Static map of Melody factory preset IDs to names. Useful when the model wants to refer to a factory preset by name.

```json
{"0": "Jazz", "1": "Pop", "2": "Rock", "3": "Dance",
 "4": "R&B", "5": "Classic", "6": "Hip-Pop"}
```

## Write

### `set_band(index, freq, gain, q, filter_type="PEAK") -> {ok, ...}`

Modifies one band on the live EQ. The change is volatile until a subsequent `save_to_user(...)`.

- `index`: zero-based, `0..9` on Melody
- `freq`: integer Hz, `20..20000`
- `gain`: float dB, `-24.0..+24.0`
- `q`: float, `0.01..100.0`
- `filter_type`: one of `PEAK`, `LOW_SHELF`, `HIGH_SHELF`, `BAND_PASS`, `LOW_PASS`, `HIGH_PASS`, `ALL_PASS`

The library validates ranges and raises a `ValueError` on out-of-range input — surfaces as an MCP tool error.

### `set_preamp(db: float) -> {ok, preamp_db}`

Global pre-amp gain in dB.

### `set_preset(preset_id: int) -> {ok, preset_id}`

Activates the given preset. Accepts only `0..9` and `240`:

- `0..6`: Jazz / Pop / Rock / Dance / R&B / Classic / Hip-Pop (factory)
- `7..9`: USER1 / USER2 / USER3
- `240`: explicit bypass (web UI's "Close EQ")

Any other ID raises a `ValueError` — including the legacy `160..162`, which would drop Melody to bypass instead of activating a USER slot. Use `set_user_slot(...)` if you only need slot semantics.

### `set_user_slot(slot: int) -> {ok, slot}`

Activates USER1, USER2, or USER3 by slot number `1/2/3`. Internally calls `set_preset(7|8|9)`.

## Destructive (confirm with user first)

### `save_to_user(slot: int) -> {ok, slot, destructive: true}`

Persists the current live EQ to the given USER slot (1/2/3). Overwrites prior contents. EEPROM-verified to survive USB power cycles.

### `reset_eq() -> {ok, destructive: true}`

Flattens the currently active slot.

### `apply_autoeq(parametric_eq_text: str, slot: int = 1) -> {ok, slot, preamp_db, bands_parsed, bands_written, truncated, destructive}`

Parses an AutoEQ `ParametricEQ.txt` and writes it to the given USER slot. End-to-end: switches to the slot, sets pre-amp, writes the bands, persists with `save_to_user`. The `parametric_eq_text` argument is the literal file content, e.g. what you would get from <https://github.com/jaakkopasanen/AutoEq>.

Band-count truncation: if the source has more bands than the device exposes (the Melody has 10), the surplus is dropped at the wire. The return value carries:

- `bands_parsed`: number of bands read from the input text
- `bands_written`: number actually applied to the device
- `truncated`: `true` when `bands_parsed > bands_written` — surface this to the user, because the dropped bands are typically the top-end corrections

The MCP client (model) should warn the user whenever `truncated` is true.

## Error surfacing

Every tool runs through `MelodyPEQ` as a context manager. Any of the following propagate as MCP tool errors with a descriptive message:

| Error | Cause |
|---|---|
| `MelodyPEQError: No FiiO HID device found` | Melody not connected / not powered |
| `NotAMelodyError` | A FiiO device is connected, but its product string does not identify as the Melody |
| `MelodyPEQError: Failed to open Melody HID device` | Another app (FiiO Control web/desktop, or another MCP session) is holding the device |
| `ValueError` | Out-of-range argument (freq/gain/q, invalid preset_id, etc.) |
