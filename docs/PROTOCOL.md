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
| Range | Meaning |
|-------|---------|
| `0..10` | Factory presets (read-only) |
| `160..169` | USER1..USER10 (writable) |
| `240` | Bypass |

The Melody is documented to expose USER1..USER3 (`160..162`); other slots in
this range are reserved for devices with more user storage.

## Melody-specific notes

- The Melody is USB-only — there is no BLE control path, so settings that on
  the K13 R2R live on BLE (SPDIF toggle, input source, etc.) are not part of
  the EQ subset documented here and are not implemented by this library.
- The Melody reports **10 PEQ bands** (verified on hardware), not the 5 that
  some older documentation suggests. `MelodyPEQ` queries `EQ_COUNT` at runtime
  so this is handled transparently.
- The Melody **does not respond to `EQ_SWITCH` (0x1A)** — neither GET nor SET
  produces a response. Verified on hardware. The mechanism it uses for EQ
  bypass is undocumented; `Preset = 240` (bypass) may be the intended path.
  As a result, `get_eq_enabled()` returns `None` on Melody, and `set_eq_enabled()`
  cannot be relied upon.
- The Melody's GET responses contain non-zero bytes in positions that the K13
  protocol documents as `0x00` padding (e.g. byte 3 of the response, and the
  byte before the `0xEE` stop sentinel). The library's response parser only
  reads the `CMD` and `LEN` fields, so these bytes do not affect decoding,
  but they hint that the Melody firmware uses those bytes for an as-yet
  undocumented purpose.
- The Melody exposes preset IDs outside the documented `160..162` / `240`
  range. Values like `0` and `9` have been observed in the wild for an
  unsaved live/custom state and possibly a "last touched band index" echo.
  These are not yet understood; treat any value outside the documented set
  as opaque.

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
