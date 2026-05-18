"""Command-line interface for snowsky-melody-peq.

Examples
--------

  melody-peq dump
  melody-peq apply HE-X4_ParametricEQ.txt --slot 1
  melody-peq preset 7         # switch to USER1
  melody-peq preset 240       # bypass EQ (Melody's "Close EQ")
  melody-peq reset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .autoeq import parse_autoeq
from .controller import MELODY_USER_SLOTS, MelodyPEQ, MelodyPEQError


def _cmd_dump(_: argparse.Namespace) -> int:
    with MelodyPEQ() as dev:
        print(f"Device  : {dev.name}")
        eq = dev.get_eq_enabled()
        print(f"EQ on   : {eq if eq is not None else 'unknown (no response)'}")
        preset = dev.get_preset()
        print(f"Preset  : {preset if preset is not None else 'unknown (no response)'}")
        preamp = dev.get_preamp()
        print(f"Pre-amp : {f'{preamp:+.1f} dB' if preamp is not None else 'unknown (no response)'}")
        count = dev.get_band_count()
        print(f"Bands   : {count if count is not None else 'unknown (no response)'}")
        print()
        for band in dev.get_all_bands():
            print(f"  {band}")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    preamp, bands = parse_autoeq(Path(args.file))
    print(f"Parsed: preamp={preamp:+.1f} dB, {len(bands)} bands")
    with MelodyPEQ() as dev:
        n = dev.get_band_count()
        if n is None:
            raise MelodyPEQError(
                "Could not read the device's PEQ band count; refusing to apply."
            )
        if len(bands) > n:
            print(f"Warning: Melody has {n} bands; truncating from {len(bands)}",
                  file=sys.stderr)
            bands = bands[:n]
        dev.set_user_slot(args.slot)
        # set_eq_enabled() is a silent no-op on Melody — bypass is
        # controlled via set_preset(240). See docs/PROTOCOL.md.
        dev.set_preamp(preamp)
        dev.set_bands(bands)
        dev.save_to_user(args.slot)
        print(f"Saved to USER{args.slot}")
    return 0


_VALID_PRESET_IDS = (*range(0, 10), 240)


def _cmd_preset(args: argparse.Namespace) -> int:
    if args.id not in _VALID_PRESET_IDS:
        raise ValueError(
            f"preset id must be in 0..9 or 240, got {args.id}. "
            f"USER slots are 7/8/9, factory presets are 0..6, bypass is 240."
        )
    with MelodyPEQ() as dev:
        dev.set_preset(args.id)
        print(f"Active preset set to {args.id}")
    return 0


def _cmd_reset(_: argparse.Namespace) -> int:
    with MelodyPEQ() as dev:
        dev.reset_eq()
        print("Current slot reset")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="melody-peq",
        description="USB HID PEQ control for the FiiO SnowSky Melody",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = p.add_subparsers(dest="command", required=True)

    sp_dump = sub.add_parser("dump", help="Show current EQ state")
    sp_dump.set_defaults(func=_cmd_dump)

    sp_apply = sub.add_parser("apply", help="Apply an AutoEQ ParametricEQ.txt file")
    sp_apply.add_argument("file", help="Path to AutoEQ ParametricEQ.txt")
    sp_apply.add_argument("--slot", type=int, choices=MELODY_USER_SLOTS, default=1,
                          help="USER slot 1-3 to persist into (default 1)")
    sp_apply.set_defaults(func=_cmd_apply)

    sp_preset = sub.add_parser(
        "preset",
        help="Switch active preset by ID (0..9 = factory/USER, 240 = bypass)",
    )
    sp_preset.add_argument(
        "id", type=int,
        help="Preset ID: 0=Jazz 1=Pop 2=Rock 3=Dance 4=R&B 5=Classic "
             "6=Hip-Pop 7=USER1 8=USER2 9=USER3 240=bypass",
    )
    sp_preset.set_defaults(func=_cmd_preset)

    sp_rst = sub.add_parser("reset", help="Clear EQ on the currently selected slot")
    sp_rst.set_defaults(func=_cmd_reset)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except MelodyPEQError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
