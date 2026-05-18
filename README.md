# snowsky-melody-peq

USB HID parametric-EQ control for the **FiiO SnowSky Melody**, in Python.

> **한국어 README**: [`README.ko.md`](README.ko.md)

> **Disclaimer.** This is an unofficial, personal project. It is not affiliated with, endorsed by, or sponsored by Guangzhou FiiO Electronics Technology Co., Ltd. "FiiO" and "SnowSky" are trademarks of their respective owner and are used here only to indicate device compatibility.

Set the Melody's parametric EQ from a Python script or shell — no Android phone, no browser. The library refuses to touch any USB device other than the SnowSky Melody, so it's safe to run blindly with other DACs attached.

## What it does

- Read and write all of the Melody's PEQ bands (frequency, gain, Q, filter type).
- Adjust the global pre-amp.
- Switch USER preset slots (USER1..USER3) and persist EQ to them.
- Import community-tuned PEQ profiles from [AutoEq](https://github.com/jaakkopasanen/AutoEq).
- CLI: `melody-peq dump | apply | preset | reset`.

## What it does NOT do

- Does not control any other FiiO device. If you connect, say, a K13 or a BTR17, the library raises `NotAMelodyError` and exits cleanly.
- Does not change Melody settings outside of EQ (no SPDIF toggle, no DAC filter, no firmware update). Use the FiiO Control Android app for those.
- Does not handle audio I/O. This is a control-plane library only.

## Installation

> **한국어 설치 안내서**가 필요하시면 [`docs/INSTALL.ko.md`](docs/INSTALL.ko.md)를 참고하세요 (conda 기준).

Install into an isolated virtual environment so the project's dependencies (notably `hidapi`) don't collide with your system Python.

**With conda** (recommended if you already use it):

```bash
conda create -n melody python=3.12 -y
conda activate melody

git clone https://github.com/dialektike/snowsky-melody-peq
cd snowsky-melody-peq
pip install -e .
```

**With venv** (Python stdlib, no extra tools):

```bash
git clone https://github.com/dialektike/snowsky-melody-peq
cd snowsky-melody-peq

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

Verify:

```bash
melody-peq --version
```

That's it on macOS and Windows. The library uses [hidapi](https://github.com/libusb/hidapi) which talks to the OS's native HID stack — no `libusb`, no Zadig driver replacement. Each new shell will need `conda activate melody` (or `source .venv/bin/activate`) before `melody-peq` is on PATH.

### Linux: udev rule for non-root access

```bash
sudo cp udev/99-fiio.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```
Replug the Melody after installing the rule.

## Quick start

```python
from snowsky_melody_peq import MelodyPEQ, FilterType

with MelodyPEQ() as dev:
    print(f"Device: {dev.name}, {dev.get_band_count()} bands")

    dev.set_user_slot(1)             # switch to USER1
    dev.set_preamp(-3.0)
    dev.set_band(0, freq=80,   gain=+4.0, q=0.71, filter_type=FilterType.LOW_SHELF)
    dev.set_band(1, freq=2500, gain=-3.5, q=1.41, filter_type=FilterType.PEAK)
    dev.save_to_user(slot=1)         # persist to USER1
```

Applying an AutoEQ profile:

```python
from snowsky_melody_peq import MelodyPEQ, parse_autoeq

preamp, bands = parse_autoeq("HE-X4_ParametricEQ.txt")
with MelodyPEQ() as dev:
    n = dev.get_band_count()
    dev.set_user_slot(1)
    dev.set_preamp(preamp)
    dev.set_bands(bands[:n])
    dev.save_to_user(slot=1)
```

From the shell:

```bash
melody-peq dump
melody-peq apply HE-X4_ParametricEQ.txt --slot 1
melody-peq preset 7              # switch to USER1
melody-peq preset 240             # bypass EQ
```

See [`examples/`](examples/) for more.

## API at a glance

| Method | Purpose |
|---|---|
| `get_band_count() / get_eq_enabled() / get_preset() / get_preamp()` | Read state — returns `T \| None` (`None` = no device response) |
| `get_band(i) / get_all_bands()` | Read PEQ bands |
| `get_preset_name(i) / get_user_slot_name(1..3)` | Read preset/slot stored name |
| `set_eq_enabled(on) / set_user_slot(1..3) / set_preset(id) / set_preamp(db)` | Set state |
| `set_band(i, freq, gain, q, filter_type) / set_bands(list)` | Write PEQ |
| `save_to_user(slot) / reset_eq()` | Persist (slots 1-3) or clear |

`FilterType` values: `PEAK`, `LOW_SHELF`, `HIGH_SHELF`, `BAND_PASS`, `LOW_PASS`, `HIGH_PASS`, `ALL_PASS`.

`Band` validates its arguments at construction: `freq` 20–20000 Hz, `gain`
±24 dB, `Q` 0.01–100. Out-of-range values raise `ValueError`.

The Melody exposes USER slots 1–3. **Activation IDs are `7..9`** (not the `160..162` of the K13 R2R docs — sending those on Melody causes bypass). Preset ID `240` is the explicit bypass. Factory presets occupy IDs `0..6` (Jazz, Pop, Rock, Dance, R&B, Classic, Hip-Pop) and are read-only.

`set_user_slot(1..3)` and `save_to_user(1..3)` use the 1/2/3 slot number; the library translates to the right activation ID internally. `get_user_slot_name(1..3)` looks up the stored name (which the device keeps under a separate legacy ID scheme — see `docs/PROTOCOL.md`).

### Melody-specific quirks (observed on real hardware)

- The Melody **does not respond to `EQ_SWITCH` (CMD `0x1A`)**, so
  `get_eq_enabled()` returns `None` on Melody. The intended bypass path is
  `set_preset(240)`. See `docs/PROTOCOL.md` for the full quirk list.
- The Melody reports **10 PEQ bands**.
- Preset IDs use a dual scheme: activation is sequential `0..9` + `240`,
  but stored slot names live at the legacy `160..162` addresses.
- `get_preset()` is a "Personal / Modified" indicator rather than a
  "currently selected slot" query — it returns the tile ID only when the
  web UI just clicked it, and returns `0` after any programmatic
  `set_preset()` / `set_band()` call. The bands themselves
  (`get_all_bands()`) are always accurate. Track the active slot in your
  application state.
- `save_to_user(slot=1..3)` persists across USB power cycles
  (end-to-end EEPROM verification).

## How it works

The library talks to the Melody over USB HID interface 3 using the same packet format as the FiiO Control Android app and web interface:

```
GET: [0xBB, 0x0B, 0x00, 0x00, CMD, LEN, ...DATA, 0x00, 0xEE]
SET: [0xAA, 0x0A, 0x00, 0x00, CMD, LEN, ...DATA, 0x00, 0xEE]
```

The full EQ command set and field encodings are documented in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Safety

This library ships **only** EQ command codes (`0x15`–`0x1B`, `0x30`). It does not implement, expose, or accept arbitrary command codes — firmware-update or factory-reset commands cannot accidentally be sent. The Melody-only identity check on connect adds a second layer: even if you have other FiiO devices attached, those won't be touched.

## Credits

- [SmookeyDev/fiio-k13-control](https://github.com/SmookeyDev/fiio-k13-control) — original reverse engineering of the FiiO Control APK v4.0.3. The K13 R2R and the Melody share the same EQ command space, so the protocol documentation derived from that work applies here.
- [AutoEq](https://github.com/jaakkopasanen/AutoEq) — community-tuned headphone PEQ database.
- [hidapi](https://github.com/libusb/hidapi) — cross-platform HID library.

## License

MIT — see [LICENSE](LICENSE).
