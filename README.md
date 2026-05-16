# snowsky-melody-peq

USB HID parametric-EQ control for the **FiiO SnowSky Melody**, in Python.

> **Disclaimer.** This is an unofficial, community-maintained project. It is not affiliated with, endorsed by, or sponsored by Guangzhou FiiO Electronics Technology Co., Ltd. "FiiO" and "SnowSky" are trademarks of their respective owner and are used here only to indicate device compatibility.

Set the Melody's parametric EQ from a Python script or shell — no Android phone, no browser. The library refuses to touch any USB device other than the SnowSky Melody, so it's safe to run blindly with other DACs attached.

## What it does

- Read and write all of the Melody's PEQ bands (frequency, gain, Q, filter type).
- Adjust the global pre-amp.
- Switch USER preset slots (USER1..USER3) and persist EQ to them.
- Import community-tuned PEQ profiles from [AutoEq](https://github.com/jaakkopasanen/AutoEq).
- CLI: `melody-peq dump | apply | toggle | reset`.

## What it does NOT do

- Does not control any other FiiO device. If you connect, say, a K13 or a BTR17, the library raises `NotAMelodyError` and exits cleanly.
- Does not change Melody settings outside of EQ (no SPDIF toggle, no DAC filter, no firmware update). Use the FiiO Control Android app for those.
- Does not handle audio I/O. This is a control-plane library only.

## Installation

> **한국어 설치 안내서**가 필요하시면 [`docs/INSTALL.ko.md`](docs/INSTALL.ko.md)를 참고하세요 (conda 기준).

```bash
git clone https://github.com/dialektike/snowsky-melody-peq
cd snowsky-melody-peq
pip install -e .
```

That's it on macOS and Windows. The library uses [hidapi](https://github.com/libusb/hidapi) which talks to the OS's native HID stack — no `libusb`, no Zadig driver replacement.

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
    dev.set_eq_enabled(True)
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
melody-peq toggle on
```

See [`examples/`](examples/) for more.

## API at a glance

| Method | Purpose |
|---|---|
| `get_band_count() / get_eq_enabled() / get_preset() / get_preamp()` | Read state |
| `get_band(i) / get_all_bands()` | Read PEQ bands |
| `set_eq_enabled(on) / set_user_slot(1..3) / set_preset(id) / set_preamp(db)` | Set state |
| `set_band(i, freq, gain, q, filter_type) / set_bands(list)` | Write PEQ |
| `save_to_user(slot) / reset_eq()` | Persist (slots 1-3) or clear |

`FilterType` values: `PEAK`, `LOW_SHELF`, `HIGH_SHELF`, `BAND_PASS`, `LOW_PASS`, `HIGH_PASS`, `ALL_PASS`.

The Melody exposes USER slots 1–3 (preset IDs `160..162`). Preset ID `240` is bypass. Factory presets (`0..10`) are read-only.

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
