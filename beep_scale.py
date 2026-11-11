"""
Play a C major scale with winsound.Beep at regular intervals, to check beep timing.

Each note starts at a scheduled time (not after a fixed sleep), so any unevenness you
hear comes from the audio output, not from the script. The printed times show when
each Beep call started and how long it blocked.

Example:
    uv run beep_scale.py --interval 0.5 --beep-ms 200
"""

import argparse
import time
import winsound

C_MAJOR = [("C4", 262), ("D4", 294), ("E4", 330), ("F4", 349),
           ("G4", 392), ("A4", 440), ("B4", 494), ("C5", 523)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between note starts (default: 0.5)")
    parser.add_argument("--beep-ms", type=int, default=200, help="length of each note in ms (default: 200)")
    parser.add_argument("--repeat", type=int, default=1, help="number of times to play the scale (default: 1)")
    args = parser.parse_args()

    start = time.monotonic()
    notes = C_MAJOR * args.repeat
    for i, (name, freq) in enumerate(notes):
        time.sleep(max(0, start + i * args.interval - time.monotonic()))
        called = time.monotonic()
        winsound.Beep(freq, args.beep_ms)
        returned = time.monotonic()
        print(f"{name:>3} ({freq} Hz)  scheduled {i * args.interval:6.3f}s  "
              f"called {called - start:6.3f}s  blocked {(returned - called) * 1000:4.0f} ms", flush=True)


if __name__ == "__main__":
    main()
