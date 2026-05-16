# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05

### Added
- `MelodyPEQ` controller with the full EQ command set: read/write bands,
  pre-amp, presets, EQ on/off, save to USER slot (1-3), reset.
- Melody identity check at connection time. Raises `NotAMelodyError` for any
  other FiiO device.
- `parse_autoeq()` for ingesting AutoEQ `ParametricEQ.txt` files.
- `melody-peq` CLI with `dump`, `apply`, `toggle`, `reset` subcommands.
- Linux udev rule for non-root device access via `/dev/hidraw*`.
- Unit tests for protocol packet building, AutoEQ parsing, and identity
  check (no hardware required).
- Protocol documentation in `docs/PROTOCOL.md`.
- Korean installation guide in `docs/INSTALL.ko.md` (conda-based).

### USB backend
- Uses `hidapi` to talk to the OS HID stack directly.
- **Windows**: no Zadig driver replacement required.
- **macOS**: no `libusb` / Homebrew dependency.
- **Linux**: requires only a hidraw udev rule (provided).

### Verified on
- (none yet) Awaiting Melody verification by maintainers.

### Known limitations
- Hardware verification of Melody-specific band count and USER slot range
  has not been completed at the time of release. Values in code reflect best
  knowledge from FiiO documentation and the K13 R2R protocol analysis.
