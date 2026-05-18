# Hardware Testing Guide

This guide walks through verifying the library against a real SnowSky
Melody using `examples/hardware_test.py` with the official FiiO web UI
for visual ground-truth.

> 한국어 버전: [`HARDWARE_TESTING.ko.md`](HARDWARE_TESTING.ko.md)

It exists for two reasons:

- The Melody silently ignores some documented commands (`EQ_SWITCH`), so
  we cannot trust read-back for everything. The web UI is the source of
  truth for "did this SET actually do anything?".
- The library encodes Melody-specific findings (USER slots at activation
  IDs `7..9`, `save_to_user` activation-ID translation, etc. — see
  [`PROTOCOL.md`](PROTOCOL.md)) that came from running this exact
  procedure on one maintainer's unit. A second device may behave
  differently; this guide is also how you confirm it doesn't.

## What is already known (don't re-derive)

The following has been hardware-verified on macOS with hidapi 0.15.0 on
one SnowSky Melody. Skim before running tests so you know what to expect:

- 10 PEQ bands. `get_band_count()` confirms.
- USER slot activation IDs: `7` (USER1), `8` (USER2), `9` (USER3).
  Sending the legacy K13 `160..162` drops the device to bypass instead.
- Factory preset IDs: `0` Jazz, `1` Pop, `2` Rock, `3` Dance, `4` R&B,
  `5` Classic, `6` Hip-Pop.
- Explicit bypass: `set_preset(240)` → web UI highlights **Close EQ**.
- `EQ_SWITCH` (0x1A) is silently unsupported on Melody; `get_eq_enabled()`
  returns `None`, `set_eq_enabled()` cannot be readback-verified.
- `save_to_user(slot)` is hardware-verified end-to-end (EEPROM persists
  across USB power cycle) when the library sends the activation ID.
- `get_preset()` is a "Personal / Modified" indicator: returns the tile
  ID only when the user clicked it in the web UI; returns `0` after any
  programmatic `set_preset()`/`set_band()` call. See
  [`PROTOCOL.md`](PROTOCOL.md) for the per-scenario table.

## Why visual verification

Some commands on the Melody:

- Have no response from the device (`get_eq_enabled()` returns `None`).
- Update internal state without echoing on the wire (e.g. `set_preset()`).
- Have separate firmware indicators ("active tile" vs "live bands") that
  read-back queries do not expose.

Visual verification via the FiiO web UI sidesteps all of this — you see
the device's actual state in your browser tab.

## Prerequisites

- A SnowSky Melody connected over USB, working in the web UI.
- The library installed in a virtual environment (see [`README.md`](../README.md)).
- A Chromium-family browser (Chrome, Edge, Brave) for WebHID support.
- The FiiO Melody control web page open in a tab. (Check the device's
  product page for the canonical URL.)

## The connect–disconnect dance

USB HID allows exactly one application to hold the device at a time. The
workflow alternates between Python and the browser:

```
┌──────────────┐  Python runs one SET, closes device
│   Python     │ ─────────────────────────────────────►
│              │
└──────────────┘                                       ┌──────────────┐
                                                       │   Web UI     │
       ◄──────────────────────────────────── click Refresh, verify
                                                       │              │
                                                       └──────────────┘
       ◄──────────────────────────────────── click Disconnect

┌──────────────┐  Python runs next test
│   Python     │ ─────────────────────────────────────►
```

`examples/hardware_test.py` automates the Python side: every test action
opens the device, performs one operation, and closes immediately so the
web can take over.

## Running `hardware_test.py`

```bash
python examples/hardware_test.py
```

You see a menu like:

```
SnowSky Melody hardware test helper
Results will append to /…/melody-test-log.txt

Available tests:
   1. dump current state (read-only)
   2. probe preset names 0..10 + 160..162 + 240 (map USER slots)
   3. set_preset(7) — probe likely USER1 ID on Melody
   …
   q. quit

Select test:
```

For each test:

1. Type the test number, press Enter.
2. The script opens the device, runs the action, and prints
   `device closed. Switch to the FiiO web UI and connect.`
3. In the browser, click **Connect** in the FiiO web UI. Click **Refresh**
   if the displayed state looks stale. Compare what the UI shows against
   what the test claims to have done.
4. Back in the terminal, type your verdict at the prompt:
   ```
   result [pass/fail/skip + optional note]:
   ```
   Example: `pass: HIFIMAN slot is highlighted in red`. Anything you type
   is appended to `melody-test-log.txt` with a timestamp.
5. Before running the next test, click **Disconnect** in the web UI so
   Python can grab the device again.

## Recommended order

The library has already been hardware-verified; this order is the most
efficient way to confirm the findings still hold on your unit. Earlier
tests are read-only; later tests are destructive.

1. **Test 1 — dump current state.** Confirms the device is reachable.
   `EQ enabled` should print `unknown (no response)`. Save a snapshot
   for restore if needed: `melody-peq dump > ~/melody-pre-test.txt`.
2. **Test 2 — probe preset names.** Expect `160`/`161`/`162` to return
   your USER slot names; `0..10` to return garbage placeholders. If the
   USER slot names appear at IDs other than `160..162`, the library's
   `get_user_slot_name()` mapping is wrong for your unit — open an issue.
3. **Tests 3, 4, 5 — `set_preset(7|8|9)`.** Web UI should highlight
   HIFIMAN, FT5, FH3 (or whatever your USER slot tiles are named).
   If any of these activate **Close EQ** instead, the activation-ID
   mapping for USER slots differs on your unit.
4. **Test 8 — `set_preset(240)`.** Web UI should highlight **Close EQ**
   (solid red, not just a border).
5. **Tests 9, 10 — `set_preset(160)` / `set_user_slot(1)`.** Expected
   to either activate USER1 (matches our verification — `set_user_slot`
   wraps to `set_preset(7)` internally) or fall back to bypass for the
   raw `set_preset(160)` form.
6. **Tests 6, 7 — `set_eq_enabled(False)` / `(True)`.** No web change
   expected — Melody ignores `EQ_SWITCH`. Useful to confirm the
   no-response is still the case.
7. **Tests 11, 12 — `set_preamp`.** Web slider should move.
8. **Test 13 — `set_band(0, 30 Hz, +12 dB, …)`.** Web Home tab: Band 1
   should jump to 30 Hz, +12 dB, Q=0.70, LS. Audible if music is playing.
9. **Test 14 — `save_to_user(1)`.** Persists current live EQ to USER1
   (overwrites HIFIMAN — make sure that slot is acceptable to lose).
   Then run test 4 (`set_preset(8)`), then test 3 (`set_preset(7)`),
   then test 1 again — Band 0 should still be the modified value.
   That round-trip confirms the slot reload from EEPROM works.
10. **Reboot persistence (manual).** Unplug the Melody, wait 10 s, plug
    back in, run test 1. The save_to_user modification should still be
    there. This is the strongest correctness signal.
11. **Test 16 — `reset_eq()`.** Destructive. Flattens the active slot.
    Run last; you'll need to redo any tuning afterwards.

## Reporting findings

After a session:

- **`melody-test-log.txt`** — auto-populated, attach this to any issue
  or PR you open.
- **`docs/PROTOCOL.md` "Melody-specific notes"** — file a PR adding any
  newly-observed mapping that differs from what is already documented.
- **`CHANGELOG.md`** — under "Verified on" if your unit confirms the
  existing findings on a new OS / hidapi version; under "Known
  limitations" if you found something new.

If a test produces a result that contradicts the library's current
behaviour, that is a bug — open an issue with the relevant log lines
and a screenshot of the web UI.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No FiiO HID device found` | Melody unplugged, or web is holding it | Replug; click Disconnect in the web tab |
| `Failed to open Melody HID device` on Linux | udev rule missing | See [`INSTALL.ko.md`](INSTALL.ko.md) §3 |
| Web UI shows stale state after a SET | Browser cached previous read | Click **Refresh** in the web UI |
| Web UI's **Connect** button does nothing | Python still holds the device, or browser lost WebHID permission | Quit Python (or wait for `device closed.` line); re-grant permission on the lock icon if needed |
| `active preset: 0` despite `set_preset(7)` | Expected — `get_preset()` reverts to 0 ("Personal/Modified") after any programmatic SET. The bands are still loaded correctly | Verify by checking `Band 0..9` output against expected slot contents |
| `set_preset(N)` made **Close EQ** highlight in web | `N` is not a valid Melody activation ID; firmware dropped to bypass | Use IDs `0..9` or `240` only |
