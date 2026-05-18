# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05

### Added
- `MelodyPEQ` controller with the full EQ command set: read/write bands,
  pre-amp, presets, EQ on/off, save to USER slot (1-3), reset.
- Melody identity check at connection time, using a case-insensitive
  word-boundary regex on the HID product string. Raises `NotAMelodyError`
  for any other FiiO device.
- `parse_autoeq()` for ingesting AutoEQ `ParametricEQ.txt` files.
- `melody-peq` CLI with `dump`, `apply`, `toggle`, `reset` subcommands.
- Linux udev rule for non-root device access via `/dev/hidraw*`.
- Unit tests (43 total) covering protocol packet building, AutoEQ parsing,
  Band/encoder validation, identity check, and getter behaviour on
  unresponsive commands. No hardware required.
- Protocol documentation in `docs/PROTOCOL.md`, including Melody-specific
  hardware-observed quirks.
- Korean installation guide in `docs/INSTALL.ko.md` (conda-based).
- AI assistant guide in `docs/AI_ASSISTANT_GUIDE.md`.
- PEP 561 `py.typed` marker so downstream type checkers see the type hints.
- `[tool.mypy]` config in `pyproject.toml`; `mypy src/` is clean.

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
  FiiO web UI (see `docs/HARDWARE_TESTING.md`).

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
- Persisting bands via `save_to_user()` has not yet been hardware-verified
  end-to-end (write + reboot survival check).
