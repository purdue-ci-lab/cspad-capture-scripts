"""
Capture binary (1-bit) frames from a cSPAD after a countdown and save them as quanta HDF5.

The camera is connected before the countdown starts, so the capture begins as soon as
the countdown reaches zero. Beeps play at 3, 2 and 1 seconds, and a longer, higher beep
marks the start of the capture. With --subticks, short quiet ticks also play between
the seconds.

The output file is named <name>_<timestamp>.h5, where the timestamp is the capture start
time, and is saved in --output-dir.

Example:
    uv run capture_bin_countdown.py --exposure-us 10 --frames 1000 --countdown 5 --subticks 3 -o scene
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
COUNTDOWN_BEEP_MS = 200
SUBTICK_PITCH = 330  # Hz (E4)
SUBTICK_BEEP_MS = 30
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
    parser.add_argument("--subticks", type=int, default=0,
                        help="number of short ticks to play between each countdown second (default: 0)")
    parser.add_argument("-o", "--output", default="capture",
                        help="output name, with or without a .h5/.hdf5 extension; the capture time is "
                             "appended, e.g. scene -> scene_<timestamp>.h5 (default: capture)")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="directory to save the output in (default: output/ in this repo)")
    parser.add_argument("--port", type=int, default=9999,
                        help="command server port set in the cSPAD software (default: 9999)")
    args = parser.parse_args()
    if args.subticks < 0:
        parser.error("--subticks must be >= 0")
    return args


def timestamped_path(output_dir, name, when):
    """Return output_dir/<stem>_<timestamp><suffix>, keeping a .h5/.hdf5 extension if given."""
    name = Path(name)
    suffix = name.suffix if name.suffix.lower() in HDF5_SUFFIXES else ".h5"
    stem = name.stem if name.suffix.lower() in HDF5_SUFFIXES else name.name
    return output_dir / name.parent / f"{stem}_{when:%Y%m%d_%H%M%S}{suffix}"


def countdown(seconds, subticks=0):
    end = time.monotonic() + seconds
    for remaining in range(seconds, 0, -1):
        print(f"{remaining}...", flush=True)
        if remaining in COUNTDOWN_PITCHES:
            winsound.Beep(COUNTDOWN_PITCHES[remaining], COUNTDOWN_BEEP_MS)
        # sleep to scheduled times (rather than for fixed durations) so the beep lengths
        # don't make the countdown drift; a subtick is skipped if its time has already passed
        second_start = end - remaining
        for k in range(1, subticks + 1):
            tick_time = second_start + k / (subticks + 1)
            delay = tick_time - time.monotonic()
            if delay < 0:
                continue
            time.sleep(delay)
            winsound.Beep(SUBTICK_PITCH, SUBTICK_BEEP_MS)
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

        countdown(args.countdown, args.subticks)

        print("Capturing...", flush=True)
        capture_time = datetime.now()
        # beep in the background so it doesn't delay the capture
        threading.Thread(target=winsound.Beep, args=(CAPTURE_PITCH, CAPTURE_BEEP_MS), daemon=True).start()
        frames = cam.get_intensity(args.frames, args.exposure_us, bitDepth=1, overlap=1, im_width=im_width)

    if frames is None:
        raise SystemExit("Capture failed: the camera reported an error.")

    output_path = timestamped_path(args.output_dir, args.output, capture_time)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # T_exp is the total capture duration; with overlap on, each frame lasts one exposure
    T_exp = args.frames * args.exposure_us * 1e-6
    print(f"Saving {frames.shape} frames to {output_path}")
    spio.write_quanta_hdf5(output_path, frames, T_exp=T_exp, compression_level=1)
    print(f"Saved {frames.shape} frames to {output_path}")


if __name__ == "__main__":
    main()
