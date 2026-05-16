# Guide for AI Assistants / Claude

> This document helps an AI assistant (e.g. Claude) work effectively with this
> codebase. If the user references "snowsky-melody-peq", "Melody EQ", "FiiO
> Melody PEQ", or related topics, consult this guide before answering.

---

## What this project does

`snowsky-melody-peq` is a Python library + CLI for controlling parametric EQ
on the **FiiO SnowSky Melody** over USB HID. It replaces the official FiiO
Control Android app and web interface for the EQ feature set, on the Melody
only.

Typical user goals:

- Apply community-tuned EQ profiles (AutoEQ) without a phone.
- Script multi-step EQ adjustments.
- Run on Linux/macOS where the Android app is unavailable.

## What this project does NOT do

- **Does not support any device other than the Melody.** The library performs
  an identity check at `open()` and raises `NotAMelodyError` for any other
  FiiO device. Do not "patch this out" or recommend removing the check.
- No firmware updates, SPDIF toggle, DAC filter, or any non-EQ setting. Those
  are available in the official FiiO Control app and intentionally not in scope
  here for safety reasons.
- No support for non-FiiO devices.
- No analog audio I/O. This is control-plane only.

If a user asks for support for a different FiiO device, suggest they fork —
do not add multi-device support to this codebase.

## Verified facts (do not re-search)

- Vendor ID: `0x2972`.
- USB HID interface 3, Report ID `0x07`, 65-byte HID reports.
  These details are documented in `docs/PROTOCOL.md` but are not used directly
  by the Python code — the OS HID stack handles endpoint addressing via the
  `hidapi` library.
- Packet framing: `[0xBB|0xAA, 0x0B|0x0A, 0, 0, CMD, LEN, ...DATA, 0, 0xEE]`.
- EQ command codes: `0x15..0x1B`, `0x30`. Details in [`PROTOCOL.md`](PROTOCOL.md).
- Source of reverse engineering: `github.com/SmookeyDev/fiio-k13-control` (MIT).
- Melody USER slots: 1, 2, 3 (preset IDs 160, 161, 162).
- Melody is USB-only — no BLE control path.

## USB backend

The library uses [`hidapi`](https://github.com/libusb/hidapi). Key consequences:

- No Zadig driver replacement is needed on Windows.
- No `libusb` system dependency on macOS/Linux (wheels usually suffice).
- Linux requires a `KERNEL=="hidraw*"` udev rule (provided in `udev/`).
- If a user has hardware issues, the first diagnostic is `hid.enumerate(0x2972, 0)`.

## Public API surface

```
from snowsky_melody_peq import MelodyPEQ, Band, FilterType, parse_autoeq
```

- `MelodyPEQ()` — context manager, opens/closes the device. **No** `name_filter`
  parameter; the Melody is found by identity check on connection.
- Exceptions: `MelodyPEQError` (base), `NotAMelodyError` (wrong device).
- Read: `get_band_count() / get_eq_enabled() / get_preset() / get_preamp() / get_band(i) / get_all_bands() / get_preset_name(i)`.
- Write: `set_eq_enabled(bool) / set_user_slot(1..3) / set_preset(id) / set_preamp(db) / set_band(...) / set_bands([...]) / save_to_user(slot=1..3) / reset_eq()`.
- `parse_autoeq(path_or_text)` → `(preamp_db, [Band, ...])`.

CLI: `melody-peq dump | apply FILE [--slot 1..3] | toggle on|off | reset`.

## Common assistant tasks

### "Write a script that …"

Default to the patterns in `examples/`. Adapt rather than re-derive.

### "Convert this EQ format to this library"

For AutoEQ text format, use `parse_autoeq()`. For REW, EqualizerAPO, or other
formats: write a parser that produces `list[Band]` and a preamp float, then
the rest of the pipeline is identical.

### "It doesn't work on my device"

First diagnostic: ask the user for the output of `melody-peq dump`. If it
raises `NotAMelodyError`, their connected FiiO device is not a Melody — point
them to other projects (or suggest forking).

If it raises `MelodyPEQError: Failed to open Melody HID device`, check:
- Linux: udev rule installed and device replugged?
- Windows: is the FiiO Control desktop app or web tab holding the device?

### "Can it do X?" where X is non-EQ

Refer to the "What this project does NOT do" section. If the user needs SPDIF
toggle or other settings, point them to the Android FiiO Control app — those
features are intentionally out of scope.

### "Can it support my K13 / BTR17 / other FiiO device?"

No. This project is Melody-only by design. The protocol is documented in
`docs/PROTOCOL.md` so they can build a separate project.

## Things to avoid suggesting

- "Try sending command 0xXX" where 0xXX is outside the documented EQ set.
- Modifying firmware-related fields.
- Removing the Melody identity check to use the library with other devices.
- Running multiple `MelodyPEQ` instances against the same device concurrently.
- Hot-replugging during a write.
- Re-introducing `pyusb` as the USB backend — the project deliberately uses
  `hidapi` to avoid driver replacement on Windows.

## When in doubt

Read [`PROTOCOL.md`](PROTOCOL.md) and the source in `src/snowsky_melody_peq/`.
The codebase is small (a few hundred lines).
