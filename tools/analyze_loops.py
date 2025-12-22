#!/usr/bin/env python3
"""Loop point continuity analyzer for elmulti files.

Analyzes WAV files and their corresponding elmulti definitions to check
if loop points are seamless (samples[loop_end] == samples[loop_start]).

Features:
- Loop continuity analysis
- Single-cycle vs normal loop classification
- Pitch estimation from loop length
- Detailed statistics by category

Usage:
    analyze_loops.py <elmulti_dir>           # Analyze single instrument
    analyze_loops.py <parent_dir> --all      # Analyze all subdirectories

Copyright (c) 2025, elmconv contributors
"""

import argparse
import math
import struct
import sys
import wave
from pathlib import Path


# =============================================================================
# Constants
# =============================================================================

DEFAULT_SAMPLE_RATE = 48000
DEFAULT_SINGLE_CYCLE_THRESHOLD = 512


# =============================================================================
# Utility Functions
# =============================================================================


def midi_to_freq(midi_note):
    """Convert MIDI note number to frequency (A4=440Hz)."""
    return 440 * (2 ** ((midi_note - 69) / 12))


def freq_to_midi(freq):
    """Convert frequency to MIDI note number with cents deviation.

    Returns:
        tuple: (midi_note, cents_deviation)
    """
    if freq <= 0:
        return 0, 0
    midi = 69 + 12 * math.log2(freq / 440)
    note = round(midi)
    cents = (midi - note) * 100
    return note, cents


def midi_to_note_name(midi_note):
    """Convert MIDI note number to note name (e.g., 60 -> 'C4')."""
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi_note // 12) - 1
    note = note_names[midi_note % 12]
    return f"{note}{octave}"


def loop_length_to_pitch(loop_length, sample_rate=DEFAULT_SAMPLE_RATE):
    """Calculate pitch information from loop length.

    Args:
        loop_length: Length of the loop in samples
        sample_rate: Sample rate in Hz

    Returns:
        dict: Pitch information (freq, midi, note_name, cents)
    """
    if loop_length <= 0:
        return None

    freq = sample_rate / loop_length
    midi, cents = freq_to_midi(freq)
    note_name = midi_to_note_name(midi)

    return {
        "freq": freq,
        "midi": midi,
        "note_name": note_name,
        "cents": cents,
    }


# =============================================================================
# WAV Reading
# =============================================================================


def read_wav_samples(filepath):
    """Read sample data from WAV file.

    Args:
        filepath: Path to WAV file

    Returns:
        tuple: (samples list, sample_width in bytes, sample_rate)
    """
    with wave.open(filepath, "rb") as w:
        sampwidth = w.getsampwidth()
        nframes = w.getnframes()
        sample_rate = w.getframerate()
        data = w.readframes(nframes)

        if sampwidth == 3:  # 24-bit
            samples = []
            for i in range(0, len(data), 3):
                b = data[i : i + 3]
                val = int.from_bytes(b, "little", signed=True)
                samples.append(val)
            return samples, sampwidth, sample_rate
        elif sampwidth == 2:  # 16-bit
            fmt = f"<{nframes}h"
            return list(struct.unpack(fmt, data)), sampwidth, sample_rate
        elif sampwidth == 1:  # 8-bit
            fmt = f"<{nframes}b"
            return list(struct.unpack(fmt, data)), sampwidth, sample_rate
    return [], 0, 0


# =============================================================================
# Elmulti Parsing
# =============================================================================


def parse_elmulti(filepath):
    """Parse elmulti file and extract sample slot information.

    Args:
        filepath: Path to elmulti file

    Returns:
        list: List of dicts with sample info (sample, loop_start, loop_end, loop_mode)
    """
    with open(filepath, "r") as f:
        content = f.read()

    samples = []
    current_sample = {}

    for line in content.split("\n"):
        line = line.strip()

        if line.startswith("sample = "):
            if current_sample:
                samples.append(current_sample)
            current_sample = {"sample": line.split("'")[1]}

        elif line.startswith("loop-start = "):
            current_sample["loop_start"] = int(line.split("=")[1].strip())

        elif line.startswith("loop-end = "):
            current_sample["loop_end"] = int(line.split("=")[1].strip())

        elif line.startswith("loop-mode = "):
            current_sample["loop_mode"] = line.split("'")[1]

    if current_sample:
        samples.append(current_sample)

    return samples


# =============================================================================
# Analysis Functions
# =============================================================================


def analyze_loop_continuity(wav_path, loop_start, loop_end):
    """Analyze loop point continuity.

    Args:
        wav_path: Path to WAV file
        loop_start: Loop start sample index
        loop_end: Loop end sample index

    Returns:
        dict: Analysis results
    """
    samples, sampwidth, sample_rate = read_wav_samples(wav_path)

    if not samples:
        return {"error": "Could not read WAV file"}

    total_samples = len(samples)

    if loop_end >= total_samples:
        return {"error": f"loop_end ({loop_end}) >= total samples ({total_samples})"}

    if loop_start < 0:
        return {"error": f"loop_start ({loop_start}) is negative"}

    val_start = samples[loop_start]
    val_end = samples[loop_end]
    diff = abs(val_end - val_start)

    # Normalize to percentage of max value
    max_val = (2 ** (sampwidth * 8 - 1)) - 1
    diff_percent = (diff / max_val) * 100

    # Calculate loop length (inclusive: loop_end is played as part of the loop)
    loop_length = loop_end - loop_start + 1

    # Calculate pitch info
    pitch_info = loop_length_to_pitch(loop_length, sample_rate)

    return {
        "total_samples": total_samples,
        "sample_rate": sample_rate,
        "bit_depth": sampwidth * 8,
        "loop_start": loop_start,
        "loop_end": loop_end,
        "loop_length": loop_length,
        "val_at_start": val_start,
        "val_at_end": val_end,
        "diff": diff,
        "diff_percent": diff_percent,
        "max_val": max_val,
        "pitch_info": pitch_info,
    }


def analyze_instrument(elmulti_dir, verbose=False, single_cycle_threshold=512):
    """Analyze all samples in an instrument directory.

    Args:
        elmulti_dir: Directory containing elmulti file and WAV files
        verbose: Print detailed information
        single_cycle_threshold: Max loop length to consider as single-cycle

    Returns:
        dict: Summary of analysis
    """
    elmulti_dir = Path(elmulti_dir)

    # Find elmulti file
    elmulti_files = list(elmulti_dir.glob("*.elmulti"))
    if not elmulti_files:
        return {"error": "No .elmulti file found"}

    elmulti_path = elmulti_files[0]
    instrument_name = elmulti_path.stem

    # Parse elmulti
    sample_slots = parse_elmulti(elmulti_path)

    results = {
        "instrument": instrument_name,
        "elmulti_path": str(elmulti_path),
        "samples": [],
        "has_loops": False,
        "max_diff_percent": 0,
        "worst_sample": None,
        "loop_length": None,
        "is_single_cycle": False,
        "pitch_info": None,
    }

    for slot in sample_slots:
        sample_name = slot.get("sample")
        loop_mode = slot.get("loop_mode", "Off")

        wav_path = elmulti_dir / sample_name

        sample_result = {
            "name": sample_name,
            "loop_mode": loop_mode,
        }

        if loop_mode != "Off" and "loop_start" in slot and "loop_end" in slot:
            results["has_loops"] = True
            loop_start = slot["loop_start"]
            loop_end = slot["loop_end"]
            loop_length = loop_end - loop_start + 1  # inclusive

            # Store loop length for first looped sample
            if results["loop_length"] is None:
                results["loop_length"] = loop_length
                results["is_single_cycle"] = loop_length <= single_cycle_threshold

            if wav_path.exists():
                analysis = analyze_loop_continuity(str(wav_path), loop_start, loop_end)
                sample_result.update(analysis)

                if "diff_percent" in analysis:
                    if analysis["diff_percent"] > results["max_diff_percent"]:
                        results["max_diff_percent"] = analysis["diff_percent"]
                        results["worst_sample"] = sample_name

                if "pitch_info" in analysis and results["pitch_info"] is None:
                    results["pitch_info"] = analysis["pitch_info"]
            else:
                sample_result["error"] = f"WAV file not found: {wav_path}"
        else:
            sample_result["loop_mode"] = "Off"

        results["samples"].append(sample_result)

    return results


# =============================================================================
# Output Functions
# =============================================================================


def get_status(diff_percent):
    """Get status string and symbol from diff percentage."""
    if diff_percent < 0.1:
        return "EXCELLENT", "✓✓"
    elif diff_percent < 1.0:
        return "GOOD", "✓"
    elif diff_percent < 5.0:
        return "FAIR", "~"
    else:
        return "POOR", "✗"


def print_analysis(
    results, verbose=False, show_pitch=False, single_cycle_threshold=512
):
    """Print analysis results in a formatted way."""
    if "error" in results:
        print(f"  Error: {results['error']}")
        return

    instrument = results["instrument"]
    has_loops = results["has_loops"]

    if not has_loops:
        print(f"  {instrument}: No loops")
        return

    max_diff = results["max_diff_percent"]
    loop_length = results.get("loop_length", 0)
    is_single_cycle = results.get("is_single_cycle", False)
    pitch_info = results.get("pitch_info")

    status, status_symbol = get_status(max_diff)

    # Build output line
    sc_marker = "[SC]" if is_single_cycle else "    "
    line = f"  [{status_symbol}] {sc_marker} {instrument}: "
    line += f"diff={max_diff:.2f}%, loop_len={loop_length}"

    if show_pitch and pitch_info:
        line += f", pitch={pitch_info['note_name']}({pitch_info['cents']:+.0f}c)"

    line += f" ({status})"

    print(line)

    if verbose:
        for sample in results["samples"]:
            if sample.get("loop_mode") == "Off":
                continue
            if "error" in sample:
                print(f"      {sample['name']}: ERROR - {sample['error']}")
            elif "diff_percent" in sample:
                diff = sample["diff_percent"]
                loop_len = sample.get("loop_length", 0)
                pitch = sample.get("pitch_info")
                pitch_str = ""
                if pitch:
                    pitch_str = f", {pitch['freq']:.1f}Hz ({pitch['note_name']}{pitch['cents']:+.0f}c)"
                print(
                    f"      {sample['name']}: diff={diff:.2f}%, len={loop_len}{pitch_str}"
                )


def print_detailed_summary(all_results, single_cycle_threshold=512):
    """Print detailed summary with single-cycle vs normal loop breakdown."""
    single_cycle = []
    normal_loop = []
    no_loop = []

    for r in all_results:
        if "error" in r:
            continue
        if not r["has_loops"]:
            no_loop.append(r)
        elif r.get("is_single_cycle", False):
            single_cycle.append(r)
        else:
            normal_loop.append(r)

    print(f"\n{'=' * 70}")
    print(f"詳細サマリー (閾値: {single_cycle_threshold} samples)")
    print(f"{'=' * 70}")

    # Normal loops
    print(
        f"\n【通常ループ (>{single_cycle_threshold} samples)】連続性優先 - {len(normal_loop)} 件"
    )
    print("-" * 70)
    if normal_loop:
        excellent = sum(1 for r in normal_loop if r["max_diff_percent"] < 0.1)
        good = sum(1 for r in normal_loop if 0.1 <= r["max_diff_percent"] < 1.0)
        fair = sum(1 for r in normal_loop if 1.0 <= r["max_diff_percent"] < 5.0)
        poor = sum(1 for r in normal_loop if r["max_diff_percent"] >= 5.0)
        print(f"  EXCELLENT: {excellent}  GOOD: {good}  FAIR: {fair}  POOR: {poor}")

        for r in sorted(normal_loop, key=lambda x: x["max_diff_percent"]):
            status, sym = get_status(r["max_diff_percent"])
            pitch = r.get("pitch_info")
            pitch_str = ""
            if pitch:
                pitch_str = f" | {pitch['note_name']}"
            print(
                f"    [{sym}] {r['instrument']:<20} "
                f"diff={r['max_diff_percent']:>6.2f}%  "
                f"len={r['loop_length']:>6,}{pitch_str}"
            )
    else:
        print("  (なし)")

    # Single-cycle
    print(
        f"\n【シングルサイクル (≤{single_cycle_threshold} samples)】ピッチ優先 - {len(single_cycle)} 件"
    )
    print("-" * 70)
    if single_cycle:
        excellent = sum(1 for r in single_cycle if r["max_diff_percent"] < 0.1)
        good = sum(1 for r in single_cycle if 0.1 <= r["max_diff_percent"] < 1.0)
        fair = sum(1 for r in single_cycle if 1.0 <= r["max_diff_percent"] < 5.0)
        poor = sum(1 for r in single_cycle if r["max_diff_percent"] >= 5.0)
        print(f"  EXCELLENT: {excellent}  GOOD: {good}  FAIR: {fair}  POOR: {poor}")
        print("  ※ シングルサイクルはピッチ優先のため、diff%が高くても正常")

        for r in sorted(single_cycle, key=lambda x: x["loop_length"]):
            status, sym = get_status(r["max_diff_percent"])
            pitch = r.get("pitch_info")
            pitch_str = ""
            if pitch:
                pitch_str = f" | {pitch['note_name']}({pitch['cents']:+.0f}c) {pitch['freq']:.1f}Hz"
            print(
                f"    [{sym}] {r['instrument']:<20} "
                f"diff={r['max_diff_percent']:>6.2f}%  "
                f"len={r['loop_length']:>4}{pitch_str}"
            )
    else:
        print("  (なし)")

    # No loops
    print(f"\n【ループなし】{len(no_loop)} 件")
    print("-" * 70)
    if no_loop:
        for r in sorted(no_loop, key=lambda x: x["instrument"]):
            print(f"    {r['instrument']}")
    else:
        print("  (なし)")


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Analyze loop point continuity in elmulti files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  analyze_loops.py /path/to/instrument_dir
  analyze_loops.py /path/to/output --all
  analyze_loops.py /path/to/output --all --verbose --pitch
  analyze_loops.py /path/to/output --all --detailed

Status indicators:
  [✓✓] EXCELLENT: diff < 0.1%  - Perfect or near-perfect loop
  [✓]  GOOD:      diff < 1.0%  - Good loop, minor discontinuity
  [~]  FAIR:      diff < 5.0%  - Noticeable discontinuity
  [✗]  POOR:      diff >= 5.0% - Significant discontinuity

  [SC] = Single-cycle waveform (pitch priority, diff% may be high)
""",
    )
    parser.add_argument(
        "directory",
        help="Directory to analyze (instrument dir or parent with --all)",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Analyze all subdirectories",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed per-sample analysis",
    )
    parser.add_argument(
        "--pitch",
        "-p",
        action="store_true",
        help="Show pitch information (frequency, note)",
    )
    parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        help="Show detailed summary with single-cycle vs normal breakdown",
    )
    parser.add_argument(
        "--sort",
        choices=["name", "diff", "length"],
        default="name",
        help="Sort results by name, diff percentage, or loop length (default: name)",
    )
    parser.add_argument(
        "--single-cycle-threshold",
        type=int,
        default=DEFAULT_SINGLE_CYCLE_THRESHOLD,
        metavar="N",
        help=f"Max loop length to consider as single-cycle (default: {DEFAULT_SINGLE_CYCLE_THRESHOLD})",
    )

    args = parser.parse_args()

    directory = Path(args.directory)

    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    if args.all:
        # Analyze all subdirectories
        subdirs = sorted([d for d in directory.iterdir() if d.is_dir()])

        if not subdirs:
            print(f"No subdirectories found in {directory}")
            sys.exit(1)

        print(f"Analyzing {len(subdirs)} instruments in {directory}\n")

        all_results = []
        for subdir in subdirs:
            results = analyze_instrument(
                subdir, args.verbose, args.single_cycle_threshold
            )
            all_results.append(results)

        # Sort if requested
        if args.sort == "diff":
            all_results.sort(key=lambda r: r.get("max_diff_percent", 0), reverse=True)
        elif args.sort == "length":
            all_results.sort(key=lambda r: r.get("loop_length") or 0, reverse=True)

        # Print results
        excellent_count = 0
        good_count = 0
        fair_count = 0
        poor_count = 0
        no_loop_count = 0

        for results in all_results:
            print_analysis(
                results, args.verbose, args.pitch, args.single_cycle_threshold
            )

            if "error" in results:
                continue

            if not results["has_loops"]:
                no_loop_count += 1
            elif results["max_diff_percent"] < 0.1:
                excellent_count += 1
            elif results["max_diff_percent"] < 1.0:
                good_count += 1
            elif results["max_diff_percent"] < 5.0:
                fair_count += 1
            else:
                poor_count += 1

        # Print summary
        print(f"\n{'=' * 50}")
        print("Summary:")
        print(f"  EXCELLENT (< 0.1%): {excellent_count}")
        print(f"  GOOD (< 1.0%):      {good_count}")
        print(f"  FAIR (< 5.0%):      {fair_count}")
        print(f"  POOR (>= 5.0%):     {poor_count}")
        print(f"  No loops:           {no_loop_count}")

        # Print detailed summary if requested
        if args.detailed:
            print_detailed_summary(all_results, args.single_cycle_threshold)
    else:
        # Analyze single directory
        results = analyze_instrument(
            directory, args.verbose, args.single_cycle_threshold
        )
        print_analysis(results, args.verbose, args.pitch, args.single_cycle_threshold)


if __name__ == "__main__":
    main()
