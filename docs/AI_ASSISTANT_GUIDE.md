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
  Note: SmookeyDev controls SPDIF/input source over **BLE**, not USB HID;
  USB HID in that project is EQ-only. Melody is USB-only, so the SmookeyDev
  BLE codes are not directly portable.
- Melody USER slots: **slot numbers 1/2/3 in this library**.
  - **Activation IDs** (CMD.EQ_PRESET): `7`, `8`, `9` — verified on hardware.
  - **Name-lookup IDs** (CMD.PRESET_NAME): `160`, `161`, `162` — verified.
  - Sending K13's `160..162` to EQ_PRESET on Melody causes bypass, NOT
    USER-slot activation. The library handles this internally.
- Melody factory preset IDs: `0` Jazz, `1` Pop, `2` Rock, `3` Dance, `4` R&B,
  `5` Classic, `6` Hip-Pop. Read-only.
- Melody is USB-only — no BLE control path.

## Hardware-verified Melody quirks

These are observed behaviours on real Melody hardware, not assumptions:

- **10 PEQ bands**, not the 5 some older notes suggest. `get_band_count()`
  confirms this on connection.
- **`CMD.EQ_SWITCH` (0x1A) is silently unsupported.** Neither GET nor SET
  receives a response on Melody. As a consequence:
  - `get_eq_enabled()` returns `None` on Melody (not `False`).
  - `set_eq_enabled(...)` will appear to "succeed" at the call site but the
    library cannot verify the change took effect.
  - The intended bypass mechanism is `set_preset(240)` — verified to
    highlight the web UI's **Close EQ** tile.
- **The documented preset ID set is wrong for Melody.** The K13 R2R doc says
  USER slots live at `160..162`; on Melody they live at activation IDs
  `7..9`, and `160..162` are the (separate) name-storage addresses (see
  the Verified facts section above). `save_to_user(slot)` was also wrong
  in this regard — it now sends activation ID `7..9` internally and is
  hardware-verified to persist across USB power cycles.
- **`get_preset()` is a "Personal / Modified" indicator, not a "current
  slot" query** on Melody. Verified per-scenario behaviour:
  - Web UI tile click → returns that tile's ID (Jazz → 0, Pop → 1, …).
  - Library `set_preset(N)` call → returns `0` (even though slot N's
    bands are correctly loaded into live EQ).
  - Any `set_band(...)` write → returns `0`.
  - After `save_to_user(...)` + USB power cycle → returns `0`.
  Track active slot in application state, not via `get_preset()`. The
  band content (`get_all_bands()`) is always accurate.
- **Non-zero "padding" bytes** appear in GET responses where the K13
  protocol documents `0x00` (byte 3 of the frame, and the byte before the
  `0xEE` stop). Our parser ignores these — they are likely Melody
  firmware-specific and not yet understood.

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
  parameter; the Melody is found by identity check on connection. Constructor
  validates `inter_cmd_delay >= 0`.
- Exceptions: `MelodyPEQError` (base), `NotAMelodyError` (wrong device).
- Read API — **every scalar getter returns `T | None`, where `None` means the
  device did not respond.** Do not treat `None` as a default value.
  - `get_band_count() -> int | None`
  - `get_eq_enabled() -> bool | None` (always `None` on Melody — see quirks)
  - `get_preset() -> int | None`
  - `get_preamp() -> float | None`
  - `get_band(i) -> Band | None`
  - `get_preset_name(i) -> str | None` (raw — Melody only returns names
    for `i in {160, 161, 162}`)
  - `get_user_slot_name(slot) -> str | None` (slot 1/2/3; wraps the
    raw call with the right ID mapping)
  - `get_all_bands() -> list[Band]` (empty list when count is unreadable)
- Write API: `set_eq_enabled(bool) / set_user_slot(1..3) / set_preset(id) / set_preamp(db) / set_band(...) / set_bands([...]) / save_to_user(slot=1..3) / reset_eq()`.
- `Band` validates ranges in `__post_init__` (freq 20..20000, gain ±24 dB,
  Q 0.01..100). Construction will raise `ValueError` on out-of-range values.
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
toggle or other settings, point them to the **Android FiiO Control app** —
those features are intentionally out of scope.

Important: the `fiiocontrol.fiio.com` web interface does **not** expose SPDIF
toggle for the Melody; that control is Android-only as of 2026-05. Do not
suggest the web UI as a workaround for non-EQ settings.

The Melody's USB HID command code for SPDIF/coaxial toggle is **not publicly
documented**. SmookeyDev controls that family of settings over BLE, and
Melody has no BLE path. Do not encourage probing arbitrary command codes
to find it.

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
- Treating `None` from a getter as a default value (e.g. `False` for
  `get_eq_enabled()`). It explicitly means "no response from device" and
  must surface that way to users.
- Changing getters back to returning silent defaults on missing response —
  that re-introduces the bug where `melody-peq dump` lied about EQ state.

## When in doubt

Read [`PROTOCOL.md`](PROTOCOL.md) and the source in `src/snowsky_melody_peq/`.
The codebase is small (a few hundred lines).
