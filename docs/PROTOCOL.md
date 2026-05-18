# FiiO Control USB HID Protocol — EQ Subset

This document describes the USB HID command set used by FiiO Control to
manipulate parametric EQ. The information here was reverse-engineered from
FiiO Control APK v4.0.3 by
[SmookeyDev/fiio-k13-control](https://github.com/SmookeyDev/fiio-k13-control)
on the K13 R2R, and is reproduced here as reference because the Melody
shares the same EQ command space.

This project implements this protocol only for the SnowSky Melody and refuses
to communicate with other FiiO devices. The protocol documentation itself,
however, is device-agnostic.

This document covers only the EQ subset. It does **not** describe firmware
update, BLE settings (input source, SPDIF toggle, etc.), or any other command
space.

## USB descriptors

| Property | Value |
|---|---|
| Vendor ID | `0x2972` |
| Interface number | `3` |
| Endpoint OUT | `0x02` |
| Endpoint IN | `0x83` |
| Report ID | `0x07` |
| Report size | 65 bytes (1 Report ID + 64 payload) |

Both endpoints are HID interrupt transfers.

## Frame format

A protocol packet is built first, then placed into a HID report.

### Protocol packet

```
Byte:  0    1    2  3   4    5    6 ... 6+LEN-1   6+LEN  6+LEN+1
       HEAD START 0  0  CMD  LEN  ...DATA...      0x00   0xEE
```

- `HEAD`/`START` differentiate GET vs SET:
  - GET request and response: `0xBB`, `0x0B`
  - SET request: `0xAA`, `0x0A`
- `CMD` is a single byte command code (see below).
- `LEN` is the length of `DATA` in bytes.
- Trailing `0x00 0xEE` is the packet terminator.

### HID report

```
Byte:  0           1 .. 64
       Report ID   protocol packet, zero-padded to fill the report
       (0x07)
```

## EQ command codes

| CMD | Name | Direction | DATA payload |
|-----|------|-----------|--------------|
| `0x15` | `EQ_BAND` | GET/SET | `[idx, gain_hi, gain_lo, freq_hi, freq_lo, q_hi, q_lo, filter_type]` |
| `0x16` | `EQ_PRESET` | GET/SET | `[preset_id]` |
| `0x17` | `EQ_GAIN` | GET/SET | `[gain_hi, gain_lo]` — global pre-amp |
| `0x18` | `EQ_COUNT` | GET | `[band_count]` |
| `0x19` | `EQ_SAVE` | SET | `[user_slot]` |
| `0x1A` | `EQ_SWITCH` | GET/SET | `[0 or 1]` |
| `0x1B` | `EQ_RESET` | SET | (empty) |
| `0x30` | `PRESET_NAME` | GET/SET | `[idx, ...utf8_name_bytes]` (≤ 8 byte name) |

## Field encodings

### Frequency (`u16` big-endian)
Hz as unsigned 16-bit. Typical range 20–20000.

Example: 2500 Hz → `0x09 0xC4`.

### Gain (`i16` big-endian, ×10)
dB times ten, two's-complement signed.

Example: `+2.5` dB → `0x00 0x19`. `-2.5` dB → `0xFF 0xE7`.

### Q (`u16` big-endian, ×100)
Q factor times one hundred.

Example: `Q = 0.71` → `0x00 0x47`. `Q = 1.41` → `0x00 0x8D`.

### Filter type (`u8`)
| Value | Meaning |
|-------|---------|
| `0` | Peaking |
| `1` | Low Shelf |
| `2` | High Shelf |
| `3` | Band Pass |
| `4` | Low Pass |
| `5` | High Pass |
| `6` | All Pass |

### Preset ID (`u8`)

The K13 R2R uses a single preset-ID namespace:

| Range | Meaning |
|-------|---------|
| `0..10` | Factory presets (read-only) |
| `160..169` | USER1..USER10 (writable) |
| `240` | Bypass |

**The Melody does not.** It uses two parallel ID schemes, depending on
which command you send — see the "Melody-specific notes" section below.

## Melody-specific notes

### USB / general

- The Melody is USB-only — there is no BLE control path, so settings that on
  the K13 R2R live on BLE (SPDIF toggle, input source, etc.) are not part of
  the EQ subset documented here and are not implemented by this library.
- The Melody reports **10 PEQ bands** (verified on hardware), not the 5 that
  some older documentation suggests. `MelodyPEQ` queries `EQ_COUNT` at runtime
  so this is handled transparently.
- The Melody **does not respond to `EQ_SWITCH` (0x1A)** — neither GET nor SET
  produces a response. Verified on hardware. The correct way to bypass EQ on
  Melody is `EQ_PRESET = 240` (see preset table below). `get_eq_enabled()`
  returns `None` on Melody; `set_eq_enabled()` cannot be relied upon.
- The Melody's GET responses contain non-zero bytes in positions that the K13
  protocol documents as `0x00` padding (e.g. byte 3 of the response, and the
  byte before the `0xEE` stop sentinel). The library's response parser only
  reads the `CMD` and `LEN` fields, so these bytes do not affect decoding,
  but they hint that the Melody firmware uses those bytes for an as-yet
  undocumented purpose.

### Dual preset-ID scheme (verified on hardware)

Melody uses two parallel preset-ID namespaces. **You must use the right one
for the right command.**

#### Activation IDs — for `CMD.EQ_PRESET` (0x16) SET/GET

| ID | Meaning |
|---|---|
| `0` | Factory preset: Jazz |
| `1` | Factory preset: Pop |
| `2` | Factory preset: Rock |
| `3` | Factory preset: Dance |
| `4` | Factory preset: R&B |
| `5` | Factory preset: Classic |
| `6` | Factory preset: Hip-Pop |
| `7` | USER1 (default name `HIFIMAN` on this maintainer's unit) |
| `8` | USER2 (default name `FT5`) |
| `9` | USER3 (default name `FH3`) |
| `240` | Explicit bypass (web UI's **Close EQ**) |

Sending `EQ_PRESET` with IDs in the `160..162` range — i.e. the K13 R2R USER
slot IDs — **does not switch USER slots on Melody**. The device interprets
them as invalid activation IDs and falls back to bypass.

`CMD.EQ_SAVE` (`0x19`) also expects an activation ID — sending the raw
1/2/3 slot number results in the device dropping to bypass without
persisting anything. The library's `save_to_user(slot=1..3)` translates
the slot number to `7..9` internally.

`CMD.EQ_PRESET` **GET** on Melody is not a "currently selected slot"
query — its return value depends on *how* the active state was reached
(hardware-verified):

| How the state was reached | `get_preset()` returns |
|---|---|
| User clicked a factory preset tile in the web UI (e.g. Jazz, Pop) | the tile's ID (verified `0` for Jazz, `1` for Pop) |
| User adjusted any band in the web UI (Personal/modified state) | `0` |
| Library called `set_preset(N)` (any N), no further modification | `0` — even though the slot's bands are correctly loaded into live EQ |
| Library called `save_to_user(slot)` after a `set_band` | `0`, including after a USB power cycle that reloads the slot |

The reading is best understood as a "Personal / Modified" indicator that
the web UI uses to drive its tile highlighting: it shows the tile ID only
while the live EQ exactly matches a known preset, and reverts to `0` the
moment the state is touched programmatically or modified. Library callers
should treat `get_preset()` as informational and track the active slot in
their own application state.

#### Name-lookup IDs — for `CMD.PRESET_NAME` (0x30) GET

| ID | Meaning |
|---|---|
| `160` | USER1 stored name |
| `161` | USER2 stored name |
| `162` | USER3 stored name |
| `0..10` | No user-readable name — device returns a fixed placeholder of garbage bytes |

So if you have a USER slot at activation ID `7` and want to read its name,
you must query `get_preset_name(160)`, not `get_preset_name(7)`. The library
hides this via `get_user_slot_name(slot)` which takes the 1/2/3 slot number
and looks up the right ID.

This duality is presumably a firmware compatibility shim — the K13 R2R name
storage layout is preserved, but activation is renumbered to a sequential
0–9 + 240 scheme that matches the tile layout in the FiiO web UI.

## Worked example

Setting band 0 to 80 Hz, +4.0 dB, Q = 0.71, low-shelf:

```
Protocol packet:
  AA  0A  00  00  15  08  00  00  28  00  50  00  47  01  00  EE
  ^^  ^^                                                      ^^
  SET HEAD                                                    STOP
                       ^^  ^^  ^^^^^^  ^^^^^^  ^^^^^^  ^^
                       CMD LEN  gain   freq    Q      filter
                                +40    80 Hz   71     low shelf
                                (=4.0)

HID OUT report (65 bytes total):
  07  AA 0A 00 00 15 08 00 00 28 00 50 00 47 01 00 EE  00 00 ... 00
  ^^
  Report ID
```

## Safety notes

- This library deliberately exposes **only the EQ command codes listed above**.
  Other command codes exist in the protocol (firmware update, audio routing,
  etc.) and sending those incorrectly may render the device unusable.
- `EQ_SAVE` is the only persisting operation. Without it, changes are lost on
  reboot.
- Selecting a factory preset (`0..10`) makes subsequent `EQ_BAND` writes
  ineffective on some firmware versions — switch to a USER slot first.
- This library hard-refuses to operate on any non-Melody FiiO device, even
  though the protocol itself is shared. If you want to use this protocol on
  another device, fork the project and lift the identity check.
