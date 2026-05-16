"""Back up the current EQ state to JSON, or restore from one.

Usage::

    python backup_restore.py backup  state.json
    python backup_restore.py restore state.json
"""

import argparse
import json
import sys

from snowsky_melody_peq import Band, FilterType, MelodyPEQ


def backup(path: str) -> None:
    with MelodyPEQ() as dev:
        state = {
            "device":  dev.name,
            "preamp":  dev.get_preamp(),
            "preset":  dev.get_preset(),
            "enabled": dev.get_eq_enabled(),
            "bands": [
                {
                    "index": b.index,
                    "freq":  b.freq,
                    "gain":  b.gain,
                    "q":     b.q,
                    "filter_type": int(b.filter_type),
                }
                for b in dev.get_all_bands()
            ],
        }
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved {len(state['bands'])} bands to {path}")


def restore(path: str) -> None:
    with open(path) as f:
        state = json.load(f)
    with MelodyPEQ() as dev:
        dev.set_eq_enabled(bool(state.get("enabled", True)))
        dev.set_preamp(state.get("preamp", 0.0))
        dev.set_bands([
            Band(
                index       = b["index"],
                freq        = b["freq"],
                gain        = b["gain"],
                q           = b["q"],
                filter_type = FilterType(b["filter_type"]),
            )
            for b in state["bands"]
        ])
    print(f"Restored {len(state['bands'])} bands from {path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["backup", "restore"])
    ap.add_argument("file")
    args = ap.parse_args()

    (backup if args.action == "backup" else restore)(args.file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
