"""Apply an AutoEQ ``ParametricEQ.txt`` to the SnowSky Melody.

Usage::

    python apply_autoeq.py path/to/HE-X4_ParametricEQ.txt --slot 1
"""

import argparse
import sys

from snowsky_melody_peq import MelodyPEQ, parse_autoeq_file


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="AutoEQ ParametricEQ.txt file")
    ap.add_argument("--slot", type=int, default=1, choices=[1, 2, 3],
                    help="USER slot 1-3 (default 1)")
    args = ap.parse_args()

    preamp, bands = parse_autoeq_file(args.file)
    print(f"Loaded {len(bands)} bands, preamp {preamp:+.1f} dB")

    with MelodyPEQ() as dev:
        # apply_profile() truncates to the device band count, pads the
        # rest flat, and persists. Note: on Melody, set_eq_enabled() is a
        # silent no-op (firmware ignores CMD.EQ_SWITCH). The intended
        # bypass path is set_preset(240); see docs/PROTOCOL.md.
        written, count = dev.apply_profile(preamp, bands, args.slot)
        if written < len(bands):
            print(f"Melody has only {count} bands; used the first {written}.",
                  file=sys.stderr)
        print(f"Saved {written} band(s) to USER{args.slot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
