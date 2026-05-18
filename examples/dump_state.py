"""Print current EQ state of the connected SnowSky Melody."""

from snowsky_melody_peq import MelodyPEQ


def _fmt(v, unit: str = "") -> str:
    """Render a value or 'unknown (no response)' when the device didn't answer."""
    if v is None:
        return "unknown (no response)"
    if isinstance(v, float):
        return f"{v:+.1f}{unit}"
    return f"{v}{unit}"


def main() -> None:
    with MelodyPEQ() as dev:
        print(f"Device       : {dev.name}")
        print(f"EQ enabled   : {_fmt(dev.get_eq_enabled())}")
        print(f"Active preset: {_fmt(dev.get_preset())}")
        print(f"Pre-amp      : {_fmt(dev.get_preamp(), ' dB')}")
        print(f"Band count   : {_fmt(dev.get_band_count())}")
        print()
        print("Bands:")
        for band in dev.get_all_bands():
            print(f"  {band}")


if __name__ == "__main__":
    main()
