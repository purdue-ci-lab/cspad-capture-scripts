"""
Capture binary (1-bit) frames from a cSPAD after a countdown and save them as quanta HDF5.

The camera is connected before the countdown starts, so the capture begins as soon as
the countdown reaches zero. Beeps play at 3, 2 and 1 seconds, and a longer, higher beep
marks the start of the capture.

The output file is named <name>_<timestamp>.h5, where the timestamp is the capture start
time, and is saved in --output-dir.

Example:
    uv run capture_bin_countdown.py --exposure-us 10 --frames 1000 --countdown 5 -o scene
"""

import argparse
import threading
import time
import winsound
from datetime import datetime
from pathlib import Path

import spadlib.io as spio
from spadlib import cspad

COUNTDOWN_PITCHES = {3: 440, 2: 554, 1: 659}  # Hz (A4, C#5, E5)
COUNTDOWN_BEEP_MS = 400
CAPTURE_PITCH = 880  # Hz (A5)
CAPTURE_BEEP_MS = 600
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"
HDF5_SUFFIXES = {".h5", ".hdf5"}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exposure-us", type=float, required=True,
                        help="exposure time per binary frame, in microseconds")
    parser.add_argument("--frames", type=int, required=True, help="number of frames to capture")
    parser.add_argument("--countdown", type=int, default=0,
                        help="seconds to wait before capturing (default: 0)")
    parser.add_argument("-o", "--output", default="capture",
                        help="output name, with or without a .h5/.hdf5 extension; the capture time is "
                             "appended, e.g. scene -> scene_<timestamp>.h5 (default: capture)")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="directory to save the output in (default: output/ in this repo)")
    parser.add_argument("--port", type=int, default=9999,
                        help="command server port set in the cSPAD software (default: 9999)")
    return parser.parse_args()


def timestamped_path(output_dir, name, when):
    """Return output_dir/<stem>_<timestamp><suffix>, keeping a .h5/.hdf5 extension if given."""
    name = Path(name)
    suffix = name.suffix if name.suffix.lower() in HDF5_SUFFIXES else ".h5"
    stem = name.stem if name.suffix.lower() in HDF5_SUFFIXES else name.name
    return output_dir / name.parent / f"{stem}_{when:%Y%m%d_%H%M%S}{suffix}"


def countdown(seconds):
    end = time.monotonic() + seconds
    for remaining in range(seconds, 0, -1):
        print(f"{remaining}...", flush=True)
        if remaining in COUNTDOWN_PITCHES:
            winsound.Beep(COUNTDOWN_PITCHES[remaining], COUNTDOWN_BEEP_MS)
        # sleep to the scheduled time (rather than for a fixed duration) so the beep
        # lengths don't make the countdown drift
        time.sleep(max(0, end - (remaining - 1) - time.monotonic()))


def main():
    args = parse_args()
    if args.output_dir is None:
        print(f"WARNING: --output-dir not set, saving to {DEFAULT_OUTPUT_DIR}")
        args.output_dir = DEFAULT_OUTPUT_DIR

    with cspad.cSPAD(args.port) as cam:
        im_width = max(cam.col)
        print(f"Connected: capturing {args.frames} frames of {cam.row}x{im_width} "
              f"at {args.exposure_us} us")

        countdown(args.countdown)

        print("Capturing...", flush=True)
        capture_time = datetime.now()
        output_path = timestamped_path(args.output_dir, args.output, capture_time)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # beep in the background so it doesn't delay the capture
        threading.Thread(target=winsound.Beep, args=(CAPTURE_PITCH, CAPTURE_BEEP_MS), daemon=True).start()
        cam.write_binary(output_path, args.frames, args.exposure_us, overlap=1, im_width=im_width, compression_level=1)


if __name__ == "__main__":
    main()
