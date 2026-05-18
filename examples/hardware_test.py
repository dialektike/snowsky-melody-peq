"""Interactive hardware-verification helper for the SnowSky Melody.

Each test action opens the device, performs a single SET (or read),
closes the device, then prompts you to switch to the FiiO web UI to
verify the change visually. Results are appended to ``melody-test-log.txt``
in the current directory.

Run:

    python examples/hardware_test.py

Why this exists: the Melody silently ignores some commands documented for
the K13 R2R (e.g. ``CMD.EQ_SWITCH``), and its preset semantics differ
from the protocol docs. Visual verification through the web UI is the
fastest way to ground-truth what each SET actually does on hardware.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

from snowsky_melody_peq import FilterType, MelodyPEQ

LOG_PATH = Path("melody-test-log.txt")


# ─── action helpers ─────────────────────────────────────────────

def _run(label: str, body) -> None:
    """Open the device, run ``body(dev)``, close. Then prompt for verdict."""
    print(f"\n→ {label}")
    try:
        with MelodyPEQ() as dev:
            body(dev)
    except Exception as e:
        print(f"  ! error: {e}")
        _log(label, f"error: {e}")
        return
    print("  device closed. Switch to the FiiO web UI and connect.")
    verdict = input("  result [pass/fail/skip + optional note]: ").strip()
    if verdict:
        _log(label, verdict)


def _log(label: str, verdict: str) -> None:
    ts = _dt.datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{label}\t{verdict}\n")
    print(f"  logged → {LOG_PATH}")


def _dump(dev: MelodyPEQ) -> None:
    print(f"  device       : {dev.name}")
    print(f"  EQ enabled   : {dev.get_eq_enabled()}")
    print(f"  active preset: {dev.get_preset()}")
    preamp = dev.get_preamp()
    print(f"  pre-amp      : {f'{preamp:+.1f} dB' if preamp is not None else 'unknown'}")
    count = dev.get_band_count()
    print(f"  band count   : {count if count is not None else 'unknown'}")
    for band in dev.get_all_bands():
        print(f"    {band}")


# ─── tests ──────────────────────────────────────────────────────
# Each entry: (label, callable taking MelodyPEQ).

TESTS: list[tuple[str, callable]] = [
    ("dump current state (read-only)", _dump),

    ("set_eq_enabled(False) — expect EQ off on web",
        lambda d: d.set_eq_enabled(False)),
    ("set_eq_enabled(True)  — expect EQ on on web",
        lambda d: d.set_eq_enabled(True)),

    ("set_preset(240) — expect bypass on web",
        lambda d: d.set_preset(240)),
    ("set_preset(160) — expect USER1 on web",
        lambda d: d.set_preset(160)),
    ("set_user_slot(1) — expect USER1 on web",
        lambda d: d.set_user_slot(1)),

    ("set_preamp(-6.0) — expect preamp slider at -6.0 dB",
        lambda d: d.set_preamp(-6.0)),
    ("set_preamp(0.0)  — restore preamp to 0.0",
        lambda d: d.set_preamp(0.0)),

    ("set_band(0, 30 Hz, +12 dB, Q 0.71, LOW_SHELF) — extreme boost, audible",
        lambda d: d.set_band(0, freq=30, gain=+12.0, q=0.71,
                             filter_type=FilterType.LOW_SHELF)),

    ("save_to_user(1) — persist current EQ to USER1",
        lambda d: d.save_to_user(1)),
    ("save_to_user(2) — persist current EQ to USER2",
        lambda d: d.save_to_user(2)),

    ("reset_eq() — flatten current slot (WARNING: destructive on active slot)",
        lambda d: d.reset_eq()),

    ("set_preset(0) — probe undocumented preset ID 0",
        lambda d: d.set_preset(0)),
    ("set_preset(9) — probe undocumented preset ID 9",
        lambda d: d.set_preset(9)),
]


# ─── menu ───────────────────────────────────────────────────────

def main() -> int:
    print("SnowSky Melody hardware test helper")
    print(f"Results will append to {LOG_PATH.resolve()}\n")
    while True:
        print("Available tests:")
        for i, (label, _) in enumerate(TESTS, 1):
            print(f"  {i:2d}. {label}")
        print("   q. quit")
        choice = input("\nSelect test: ").strip().lower()
        if choice in {"q", "quit", "exit", ""}:
            print("bye")
            return 0
        try:
            idx = int(choice) - 1
            label, body = TESTS[idx]
        except (ValueError, IndexError):
            print(f"unknown choice: {choice!r}\n")
            continue
        _run(label, body)


if __name__ == "__main__":
    sys.exit(main())
