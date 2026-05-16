"""Blind A/B test by toggling EQ on/off at random."""

import random
import time

from snowsky_melody_peq import MelodyPEQ


def main() -> None:
    rounds = 6
    with MelodyPEQ() as dev:
        results = []
        for r in range(rounds):
            on = bool(random.getrandbits(1))
            dev.set_eq_enabled(on)
            input(f"Round {r + 1}/{rounds}: listen, then press Enter for your guess... ")
            guess = input("  EQ on? [y/n] ").strip().lower().startswith("y")
            results.append((on, guess))
            time.sleep(0.5)

        correct = sum(1 for actual, guess in results if actual == guess)
        print(f"\nScore: {correct}/{rounds}")
        for i, (actual, guess) in enumerate(results, 1):
            mark = "✓" if actual == guess else "✗"
            print(f"  Round {i}: actual={'ON ' if actual else 'OFF'}  "
                  f"guess={'ON ' if guess else 'OFF'}  {mark}")


if __name__ == "__main__":
    main()
