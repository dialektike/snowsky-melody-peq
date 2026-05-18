# Hardware Testing Guide

This guide walks through verifying the library against a real SnowSky
Melody using `examples/hardware_test.py` and the official FiiO web UI for
visual ground-truth. It exists because the Melody silently ignores some
documented commands (`EQ_SWITCH`), so we cannot trust read-back alone —
the web UI is the source of truth.

> 한국어 버전: [`HARDWARE_TESTING.ko.md`](HARDWARE_TESTING.ko.md)

## Why visual verification

Some commands on the Melody:

- Have no response from the device (`get_eq_enabled()` returns `None`).
- Have ambiguous side effects (e.g. `set_preset(160)` might bypass instead
  of switching to a USER slot).
- Lack any acknowledgement we can trust.

Visual verification via the FiiO web UI sidesteps all of this. You see
the device's actual state in your browser.

## Prerequisites

- A SnowSky Melody connected over USB, working in the web UI.
- The library installed in a virtual environment (see [`README.md`](../README.md)).
- A Chromium-family browser (Chrome, Edge, Brave) for WebHID support.
- The FiiO Melody control web page open in a tab. (At time of writing the
  user reports it under FiiO's control site; check the device's product
  page for the canonical URL.)

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

Run tests in this order on a first pass. Earlier tests are read-only or
trivially reversible; later tests are destructive.

1. **Test 1 — dump current state.** Confirms the device is reachable and
   captures the starting EQ for reference. Pipe this to a file if you
   want a backup: `melody-peq dump > ~/melody-pre-test.txt`.
2. **Test 2 — probe preset names.** The single most informative test:
   it reads `get_preset_name()` across all candidate IDs in one pass.
   Whichever IDs return the names you set in the web (e.g. `HIFIMAN`,
   `FT5...`, `FH3`) are the device's real USER slots.
3. **Tests 3, 4, 5 — `set_preset(7|8|9)`.** Confirm whether the
   low-numbered IDs actually switch the active preset on Melody, as
   suggested by the web UI's tile layout.
4. **Tests 9, 10 — `set_preset(160)` / `set_user_slot(1)`.** Verify
   whether the documented K13 R2R USER slot IDs (160–162) do anything
   on Melody, or whether they fall back to bypass.
5. **Test 8 — `set_preset(240)`.** Confirms the bypass mechanism. The
   web UI should highlight **Close EQ**.
6. **Tests 6, 7 — `set_eq_enabled(False)` / `(True)`.** Verifies whether
   the silent `EQ_SWITCH` SET actually changes the device state, even
   though there is no response.
7. **Tests 11, 12 — `set_preamp`.** Web slider should move.
8. **Test 13 — `set_band(0, 30 Hz, +12 dB, …)`.** Extreme low-shelf
   boost — Band 0 in the web should jump to +12 dB. Audible if music
   is playing.
9. **Test 14 — `save_to_user(1)`.** Persists current EQ to USER1.
   Combine with the reboot test below.
10. **Reboot persistence (manual).** Unplug the Melody, wait 10 s, plug
    back in, run Test 1. Confirm the USER1 contents survived.
11. **Test 16 — `reset_eq()`.** Destructive. Flattens the active slot.
    Run last; you'll need to redo any tuning afterwards.

## Reporting findings

After a session, three places benefit from your notes:

- **`melody-test-log.txt`** — already auto-populated, no action needed.
- **`docs/PROTOCOL.md` "Melody-specific notes"** — file a PR adding any
  newly-confirmed mapping (e.g. "USER slots live at 7–9, not 160–162").
- **`CHANGELOG.md`** — under "Verified on" / "Known limitations".

If a test produces a result that contradicts the library's current
behaviour, that is a bug — open an issue with the relevant log lines
and (if relevant) a screenshot of the web UI.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No FiiO HID device found` | Melody unplugged, or web is holding it | Replug; click Disconnect in the web tab |
| `Failed to open Melody HID device` on Linux | udev rule missing | See [`INSTALL.ko.md`](INSTALL.ko.md) §3 |
| Web UI shows stale state after a SET | Browser cached previous read | Click **Refresh** in the web UI |
| Web UI's **Connect** button does nothing | Python still holds the device, or browser lost WebHID permission | Quit Python (or wait for `device closed.` line); re-grant permission on the lock icon if needed |
| Active preset tile stays the same after `set_preset(N)` | `N` is not a valid preset on Melody; device may have bypassed | Try the next candidate ID; check **Close EQ** highlight state |
