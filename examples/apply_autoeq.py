"""Apply an AutoEQ ``ParametricEQ.txt`` to the SnowSky Melody.

Usage::

    python apply_autoeq.py path/to/HE-X4_ParametricEQ.txt --slot 1
"""

import argparse
import sys

from snowsky_melody_peq import MelodyPEQ, parse_autoeq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="AutoEQ ParametricEQ.txt file")
    ap.add_argument("--slot", type=int, default=1, choices=[1, 2, 3],
                    help="USER slot 1-3 (default 1)")
    args = ap.parse_args()

    preamp, bands = parse_autoeq(args.file)
    print(f"Loaded {len(bands)} bands, preamp {preamp:+.1f} dB")

    with MelodyPEQ() as dev:
        n = dev.get_band_count()
        if n is None:
            print("Could not read the device's PEQ band count; aborting.",
                  file=sys.stderr)
            return 2
        if len(bands) > n:
            print(f"Melody has only {n} bands; using the first {n}.", file=sys.stderr)
            bands = bands[:n]

        dev.set_user_slot(args.slot)
        # Note: on Melody, set_eq_enabled() is a silent no-op (firmware
        # ignores CMD.EQ_SWITCH). The intended bypass path is
        # set_preset(240); see docs/PROTOCOL.md.
        dev.set_preamp(preamp)
        dev.set_bands(bands)
        dev.save_to_user(args.slot)
        print(f"Saved to USER{args.slot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
