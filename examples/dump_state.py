"""Print current EQ state of the connected SnowSky Melody."""

from snowsky_melody_peq import MelodyPEQ


def main() -> None:
    with MelodyPEQ() as dev:
        print(f"Device       : {dev.name}")
        print(f"EQ enabled   : {dev.get_eq_enabled()}")
        print(f"Active preset: {dev.get_preset()}")
        print(f"Pre-amp      : {dev.get_preamp():+.1f} dB")
        print(f"Band count   : {dev.get_band_count()}")
        print()
        print("Bands:")
        for band in dev.get_all_bands():
            print(f"  {band}")


if __name__ == "__main__":
    main()
