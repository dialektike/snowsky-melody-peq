# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06

### Changed (breaking)
- `parse_autoeq(source)`: a `str` argument is now **always treated as the
  file contents**, never as a filesystem path. Previously a single-line
  string was heuristically probed as a path, which had two failure modes:
  a mistyped path silently parsed as an empty profile `(0.0, [])`, and a
  single-line string that happened to match an existing file would read
  that file — a real concern for the MCP `apply_autoeq` tool, whose text
  argument could be steered into reading arbitrary local files. To read a
  file, pass a `Path` or use the new `parse_autoeq_file()`.
- `parse_autoeq()` re-indexes the surviving bands sequentially from 0
  after skipping `OFF` filter lines. The `Filter N` numbers in the source
  are no longer used as device indices, so an `OFF` line in the middle of
  a profile can no longer leave an index gap that preserves stale EQ on
  the device.
- `get_band()` / `get_all_bands()` no longer raise `ValueError` when the
  device reports values outside the write-side ranges (e.g. `freq=0` on a
  factory-fresh or freshly reset band). Device-reported values are now
  surfaced as-is via `Band(..., validate=False)`.

### Added
- `parse_autoeq_file(path)`: reads an AutoEQ `ParametricEQ.txt` file and
  raises the usual `FileNotFoundError` / `OSError` on a bad path, so
  typos fail loudly instead of yielding an empty profile.
- `MelodyPEQ.apply_profile(preamp, bands, slot)`: applies a complete
  profile in one call — switches to the USER slot, writes the pre-amp,
  re-indexes and truncates the bands to the device's band count, **pads
  every remaining device band flat (0 dB)** so EQ previously saved in the
  slot cannot bleed through underneath a shorter profile, then persists
  with `save_to_user()`. Returns `(bands_written, device_band_count)`.
  The CLI `apply` subcommand, the MCP `apply_autoeq` tool, and
  `examples/apply_autoeq.py` now all share this path.
- `Band(..., validate=False)` init-only flag for constructing bands from
  device-reported values without the write-side range checks. The default
  (`validate=True`) behaves exactly as before. Note: on Python 3.10/3.11,
  `dataclasses.replace()` requires `InitVar`s to be passed explicitly
  (fixed in 3.12), so `replace(band, ...)` on those versions needs
  `validate=True` spelled out.
- 13 regression tests in `tests/test_validation_fixes.py` covering all
  four fixes below (58 tests total, up from 45).

### Fixed
- `MelodyPEQ.set_band()` now constructs a `Band` internally and therefore
  enforces the documented ranges (freq 20–20000 Hz, gain ±24 dB,
  Q 0.01–100) before anything reaches the wire. Previously it bypassed
  `Band` validation entirely, so e.g. `freq=5`, `gain=30.0`, `q=0.005`
  were encoded and sent — contradicting the MCP tool docs, which claimed
  the library validated these ranges.
- Applying an AutoEQ profile no longer leaves stale EQ behind, in either
  of the two ways it previously could: index gaps from skipped `OFF`
  filters, and untouched high bands when the profile has fewer bands than
  the device (both fixed by the re-indexing + flat padding above).
- A mistyped path passed to the AutoEQ parser no longer "succeeds" with
  an empty profile (see the breaking `parse_autoeq` change above).
- Stale `fiio-peq` / `fiio_peq` references in module docstrings
  (`types.py`, `autoeq.py`) updated to the current package name.

## [0.1.0] - 2026-05

### Added
- `MelodyPEQ` controller with the full EQ command set: read/write bands,
  pre-amp, presets, EQ on/off, save to USER slot (1-3), reset.
- Melody identity check at connection time, using a case-insensitive
  word-boundary regex on the HID product string. Raises `NotAMelodyError`
  for any other FiiO device.
- `parse_autoeq()` for ingesting AutoEQ `ParametricEQ.txt` files.
- `melody-peq` CLI with `dump`, `apply`, `preset`, `reset` subcommands.
  (`preset ID` accepts factory/USER activation IDs `0..9` and `240` for
  bypass — replaces an earlier `toggle on|off` form that did not work on
  Melody because the firmware ignores `EQ_SWITCH`.)
- Linux udev rule for non-root device access via `/dev/hidraw*`.
- Unit tests (45 total) covering protocol packet building, AutoEQ parsing,
  Band/encoder validation, identity check, getter behaviour on
  unresponsive commands, and the dual-scheme USER-slot name lookup.
  No hardware required.
- Protocol documentation in `docs/PROTOCOL.md`, including Melody-specific
  hardware-observed quirks.
- Korean installation guide in `docs/INSTALL.ko.md` (conda-based).
- AI assistant guide in `docs/AI_ASSISTANT_GUIDE.md`.
- PEP 561 `py.typed` marker so downstream type checkers see the type hints.
- `[tool.mypy]` config in `pyproject.toml`; `mypy src/` is clean.
- Optional MCP server (`snowsky_melody_peq.mcp_server`) shipped under
  the `mcp` extra (`pip install snowsky-melody-peq[mcp]`). Exposes 11
  tools (`get_state`, `get_band`, `set_band`, `set_preamp`, `set_preset`,
  `set_user_slot`, `save_to_user`, `reset_eq`, `apply_autoeq`,
  `get_user_slot_name`, `list_factory_presets`) for Claude / Anthropic
  tool calling. `mcp-snowsky-melody` console script registered. Tool
  reference: `docs/MCP_TOOLS.md`.

### Defensive validation
- `Band.__post_init__` rejects out-of-range freq / gain / Q and coerces
  `filter_type` ints to `FilterType` (raises `ValueError` on invalid).
- `encode_u16` and `encode_gain` raise `ValueError` on overflow rather than
  silently wrapping to 16 bits.
- `wrap_hid_report` raises `ValueError` on packets that exceed the HID
  payload capacity (instead of silently truncating).
- `MelodyPEQ(inter_cmd_delay=...)` rejects negative values at construction.
- CLI handles `FileNotFoundError` / `OSError` / `ValueError` with a friendly
  message and exit code 2 instead of leaking a traceback.

### Getter contract
- Every scalar getter (`get_band_count`, `get_eq_enabled`, `get_preset`,
  `get_preamp`, `get_preset_name`) returns `T | None`. `None` means the
  device did not respond to the query — it is **not** a default value.
  Previously these silently returned `False`/`0`/`-1`/`0.0`/`""`, which made
  "no response" indistinguishable from a real reading.
- `melody-peq dump` renders `None` as `unknown (no response)`.

### USB backend
- Uses `hidapi` to talk to the OS HID stack directly.
- **Windows**: no Zadig driver replacement required.
- **macOS**: no `libusb` / Homebrew dependency.
- **Linux**: requires only a hidraw udev rule (provided).

### Verified on
- macOS (darwin, arm64) with Python 3.12 + hidapi 0.15.0 on a SnowSky
  Melody. Read side: `melody-peq dump` returns a coherent read of all 10
  bands, pre-amp, and preset. Write side: `set_preset(0..9)` and
  `set_preset(240)` all behave as expected when cross-checked against the
  FiiO web UI (see `docs/HARDWARE_TESTING.md`). `save_to_user(1)` was
  verified end-to-end: `set_band` modification → `save_to_user(1)` →
  switch USER slot away and back → USB unplug/replug → modification
  survives.

### Known limitations / hardware findings
- The Melody **does not respond to `CMD.EQ_SWITCH` (0x1A)** — GET nor SET.
  `get_eq_enabled()` therefore returns `None` on Melody, and
  `set_eq_enabled()` cannot be verified. Use `set_preset(240)` for EQ
  bypass instead — verified to highlight "Close EQ" in the web UI.
- The Melody reports **10 PEQ bands**, not the 5 that some older
  documentation suggested.
- **Preset IDs follow a dual scheme on Melody** (corrected from the K13
  R2R single-namespace assumption inherited from upstream docs):
  - Activation (`CMD.EQ_PRESET`): `0..6` = factory presets,
    `7..9` = USER1..USER3, `240` = bypass. **`160..162` are NOT valid
    activation IDs on Melody** — sending them falls back to bypass.
  - Name lookup (`CMD.PRESET_NAME`): `160..162` return USER slot names
    (e.g. "HIFIMAN", "FT5", "FH3"); IDs `0..10` return a firmware
    placeholder of garbage bytes (no stored names for factory presets).
  - `MELODY_PRESET_USER1` constant updated from `160` to `7` accordingly.
  - New helper `MelodyPEQ.get_user_slot_name(slot)` hides the scheme
    duality from callers.
- `save_to_user(slot)` now sends the activation ID (`7..9`) instead of
  the raw slot number (`1..3`). The raw-slot form was observed to be
  silently dropped on Melody (device went to bypass without writing).
  End-to-end EEPROM persistence verified after this fix.
- `get_preset()` (CMD.EQ_PRESET GET) is not a "current slot" query on
  Melody — it returns the tile ID only when the user clicked that tile
  in the web UI (verified `0` for Jazz, `1` for Pop), and returns `0`
  ("Personal / Modified" indicator) when the live EQ has been touched
  in any other way, including any `set_preset(N)` call from this
  library and any `set_band` modification. The bands are still
  correctly loaded in all cases — only the indicator differs.
  See `docs/PROTOCOL.md` for the full per-scenario table.
