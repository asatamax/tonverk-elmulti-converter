#!/usr/bin/env -S uv run --script
# /// script
# dependencies = []
# ///
#
# LLM AGENT NOTE: Run with --help to see usage, options, and examples.
# This tool supports both interactive wizard mode and CLI argument mode.
#
"""
Loop Calculator - Sample rate and loop point calculation tool

Calculates theoretical sample rates, cycle lengths, and ideal loop points
for audio sample conversion and editing workflows.

Usage:
  Interactive mode (wizard):  ./loop_calculator.py
  CLI mode (for LLM/scripts): ./loop_calculator.py --wav-sr 66896 --transpose -24
"""

import argparse
import math
import sys


def midi_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def midi_to_name(midi_note: int) -> str:
    """Convert MIDI note number to note name (e.g., 60 -> C3)."""
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi_note // 12) - 2  # MIDI 60 = C3
    note = note_names[midi_note % 12]
    return f"{note}{octave}"


def calculate_original_sr(wav_sr: int, transpose: int) -> float:
    """Calculate the original sample rate from WAV SR and transpose value."""
    return wav_sr * (2 ** (transpose / 12))


def samples_per_cycle(sample_rate: float, frequency: float) -> float:
    """Calculate samples per cycle for a given frequency."""
    return sample_rate / frequency


def cents_per_sample(samples_in_cycle: float) -> float:
    """Calculate pitch error in cents for 1 sample deviation."""
    if samples_in_cycle <= 0:
        return 0
    # 1 sample error ratio
    ratio = (samples_in_cycle + 1) / samples_in_cycle
    # Convert ratio to cents: 1200 * log2(ratio)
    return 1200 * math.log2(ratio)


def find_ideal_loop_lengths(samples_per_cyc: float, max_cycles: int = 16) -> list:
    """
    Find ideal loop lengths that are close to integer multiples of the cycle length.
    Returns list of (cycles, length, error_percent, error_cents)
    """
    results = []
    for n_cycles in [1, 2, 3, 4, 6, 8, 12, 16]:
        if n_cycles > max_cycles:
            break
        ideal_length = samples_per_cyc * n_cycles
        # Try both floor and ceil
        for length in [int(ideal_length), int(ideal_length) + 1]:
            if length <= 0:
                continue
            actual_cycles = length / samples_per_cyc
            error_ratio = actual_cycles / n_cycles
            error_cents = 1200 * math.log2(error_ratio) if error_ratio > 0 else 0
            error_percent = (error_ratio - 1) * 100
            results.append((n_cycles, length, error_percent, error_cents))

    # Sort by absolute error
    results.sort(key=lambda x: abs(x[3]))
    # Remove duplicates (same length)
    seen_lengths = set()
    unique_results = []
    for r in results:
        if r[1] not in seen_lengths:
            seen_lengths.add(r[1])
            unique_results.append(r)
    return unique_results[:8]


def print_separator(char: str = "=", length: int = 60):
    print(char * length)


def print_results(
    wav_sr: int,
    transpose: int,
    target_sr: int,
    midi_key: int,
    loop_start: int | None,
    loop_end: int | None,
):
    """Print all calculation results."""

    original_sr = calculate_original_sr(wav_sr, transpose)
    freq = midi_to_freq(midi_key)
    note_name = midi_to_name(midi_key)
    resample_ratio = target_sr / original_sr

    # Cycles per sample rate
    orig_spc = samples_per_cycle(original_sr, freq)
    target_spc = samples_per_cycle(target_sr, freq)

    # Print header
    print()
    print_separator("=")
    print("LOOP CALCULATOR RESULTS")
    print_separator("=")

    # Sample rate section
    print()
    print("[ Sample Rate Information ]")
    print_separator("-")
    print(f"  WAV header SR:      {wav_sr:,} Hz")
    if transpose != 0:
        print(f"  transpose:          {transpose:+d} semitones")
        print(
            f"  Original SR:        {original_sr:,.2f} Hz  (calculated from transpose)"
        )
    else:
        print("  transpose:          0 (none)")
        print(f"  Original SR:        {original_sr:,.0f} Hz")
    print(f"  Target SR:          {target_sr:,} Hz")
    print(f"  Resample ratio:     {resample_ratio:.4f}x")

    # Pitch section
    print()
    print(f"[ Pitch Information ({note_name} / MIDI {midi_key} / {freq:.2f} Hz) ]")
    print_separator("-")
    print(f"  Original SR:  1 cycle = {orig_spc:.2f} samples ({1000 / freq:.3f} ms)")
    print(f"  Target SR:    1 cycle = {target_spc:.2f} samples ({1000 / freq:.3f} ms)")

    # Error sensitivity
    print()
    print("[ 1-Sample Error Sensitivity ]")
    print_separator("-")
    orig_cents = cents_per_sample(orig_spc)
    target_cents = cents_per_sample(target_spc)
    print(f"  Original SR:  1 sample error = +/-{orig_cents:.1f} cents")
    print(f"  Target SR:    1 sample error = +/-{target_cents:.1f} cents")

    if orig_cents > 20:
        print()
        print("  WARNING: High pitch sensitivity at original SR!")
        print("           Consider extending loop by copying cycles.")

    # Loop point conversion (if provided)
    if loop_start is not None and loop_end is not None:
        loop_length = loop_end - loop_start + 1  # Inclusive
        new_start = loop_start * resample_ratio
        new_end = loop_end * resample_ratio
        new_length = new_end - new_start + 1

        print()
        print("[ Loop Point Conversion ]")
        print_separator("-")
        print(f"  Original:   start={loop_start}, end={loop_end}, length={loop_length}")
        print(
            f"  Converted:  start={new_start:.2f}, end={new_end:.2f}, length={new_length:.2f}"
        )
        print(
            f"  Rounded:    start={round(new_start)}, end={round(new_end)}, length={round(new_end) - round(new_start) + 1}"
        )

        cycles_in_loop = loop_length / orig_spc
        print(f"  Cycles in loop: ~{cycles_in_loop:.2f}")

        if loop_length < 100:
            print()
            print(
                f"  WARNING: Short loop ({loop_length} samples) - single-cycle territory!"
            )
            print("           Pitch errors will be significant. Handle with care.")

    # Ideal loop lengths
    print()
    print(f"[ Ideal Loop Lengths ({note_name} basis) ]")
    print_separator("-")

    # For original SR
    print(f"\n  Original SR ({original_sr:,.0f} Hz): 1 cycle = {orig_spc:.2f} samples")
    print(f"  {'cycles':<8} {'length':<10} {'error':<12} {'cents':<10}")
    print(f"  {'-' * 8} {'-' * 10} {'-' * 12} {'-' * 10}")
    for cycles, length, err_pct, err_cents in find_ideal_loop_lengths(orig_spc):
        mark = " <-- best" if abs(err_cents) < 1 else ""
        print(
            f"  x{cycles:<7} {length:<10} {err_pct:+.3f}%      {err_cents:+.1f}{mark}"
        )

    # For target SR
    print(f"\n  Target SR ({target_sr:,} Hz): 1 cycle = {target_spc:.2f} samples")
    print(f"  {'cycles':<8} {'length':<10} {'error':<12} {'cents':<10}")
    print(f"  {'-' * 8} {'-' * 10} {'-' * 12} {'-' * 10}")
    for cycles, length, err_pct, err_cents in find_ideal_loop_lengths(target_spc):
        mark = " <-- best" if abs(err_cents) < 1 else ""
        print(
            f"  x{cycles:<7} {length:<10} {err_pct:+.3f}%      {err_cents:+.1f}{mark}"
        )

    # Ideal loop end (if loop_start provided)
    if loop_start is not None:
        print()
        print(f"[ Ideal Loop End Points (from start={loop_start}) ]")
        print_separator("-")

        print(f"\n  Original SR ({original_sr:,.0f} Hz):")
        print(f"  {'cycles':<8} {'loop_end':<10} {'length':<10} {'cents':<10}")
        print(f"  {'-' * 8} {'-' * 10} {'-' * 10} {'-' * 10}")
        for cycles, length, err_pct, err_cents in find_ideal_loop_lengths(orig_spc)[:6]:
            loop_end_calc = loop_start + length - 1  # Inclusive end
            mark = " <-- best" if abs(err_cents) < 1 else ""
            print(
                f"  x{cycles:<7} {loop_end_calc:<10} {length:<10} {err_cents:+.1f}{mark}"
            )

        # For target SR with converted start
        converted_start = round(loop_start * resample_ratio)
        print(f"\n  Target SR ({target_sr:,} Hz, start={converted_start}):")
        print(f"  {'cycles':<8} {'loop_end':<10} {'length':<10} {'cents':<10}")
        print(f"  {'-' * 8} {'-' * 10} {'-' * 10} {'-' * 10}")
        for cycles, length, err_pct, err_cents in find_ideal_loop_lengths(target_spc)[
            :6
        ]:
            loop_end_calc = converted_start + length - 1  # Inclusive end
            mark = " <-- best" if abs(err_cents) < 1 else ""
            print(
                f"  x{cycles:<7} {loop_end_calc:<10} {length:<10} {err_cents:+.1f}{mark}"
            )

    # Crossfade recommendation
    if loop_start is not None and loop_end is not None:
        print()
        print("[ Crossfade Recommendation ]")
        print_separator("-")
        cf_length = max(4, int(loop_length * 0.05))
        print("  If loop clicks persist after optimization:")
        print(f"  Recommended crossfade: {cf_length} samples (~5% of loop)")

    print()
    print_separator("=")


def prompt_int(
    message: str, default: int | None = None, required: bool = True
) -> int | None:
    """Prompt user for integer input with optional default."""
    if default is not None:
        prompt = f"{message} [{default}]: "
    else:
        prompt = f"{message}: " if required else f"{message} (Enter to skip): "

    while True:
        try:
            value = input(prompt).strip()
            if value == "":
                if default is not None:
                    return default
                elif not required:
                    return None
                else:
                    print("  This field is required.")
                    continue
            return int(value)
        except ValueError:
            print("  Please enter a valid integer.")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)


def interactive_mode():
    """Run interactive wizard mode."""
    print()
    print_separator("=")
    print("LOOP CALCULATOR - Interactive Mode")
    print_separator("=")
    print()
    print("Answer the following questions to calculate loop parameters.")
    print("Press Enter to use default values shown in [brackets].")
    print()

    # Required
    print("--- Required ---")
    wav_sr = prompt_int("WAV sample rate (Hz)", required=True)

    print()
    print("--- Optional (press Enter for defaults) ---")
    transpose = prompt_int("transpose value (semitones)", default=0)
    target_sr = prompt_int("Target sample rate (Hz)", default=48000)
    midi_key = prompt_int("Reference MIDI key (60=C3)", default=60)

    print()
    print("--- Loop Points (optional) ---")
    loop_start = prompt_int("Loop start (sample number)", required=False)

    loop_end = None
    if loop_start is not None:
        loop_end = prompt_int("Loop end (sample number)", required=False)

    print_results(wav_sr, transpose, target_sr, midi_key, loop_start, loop_end)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate sample rates, cycle lengths, and ideal loop points for audio samples.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode (wizard):
    %(prog)s

  CLI mode with transpose:
    %(prog)s --wav-sr 66896 --transpose -24

  CLI mode with loop points:
    %(prog)s --wav-sr 66896 --transpose -24 --loop-start 4752 --loop-end 4815

  Full example:
    %(prog)s --wav-sr 66896 --transpose -24 --target-sr 48000 --key 60 --loop-start 100

Notes:
  - transpose: Negative = WAV SR is higher than original (pitch shifted up in file)
  - Loop end is inclusive (loop_length = end - start + 1)
  - Original SR = WAV_SR * 2^(transpose/12)
""",
    )

    parser.add_argument("--wav-sr", type=int, help="Sample rate from WAV header (Hz)")
    parser.add_argument(
        "--transpose",
        type=int,
        default=0,
        help="SFZ transpose value in semitones (default: 0)",
    )
    parser.add_argument(
        "--target-sr",
        type=int,
        default=48000,
        help="Target sample rate for conversion (default: 48000)",
    )
    parser.add_argument(
        "--key",
        type=int,
        default=60,
        help="Reference MIDI key number (default: 60 = C3)",
    )
    parser.add_argument(
        "--loop-start", type=int, help="Loop start point (sample number)"
    )
    parser.add_argument(
        "--loop-end", type=int, help="Loop end point (sample number, inclusive)"
    )

    args = parser.parse_args()

    # If no wav-sr provided, run interactive mode
    if args.wav_sr is None:
        interactive_mode()
    else:
        print_results(
            wav_sr=args.wav_sr,
            transpose=args.transpose,
            target_sr=args.target_sr,
            midi_key=args.key,
            loop_start=args.loop_start,
            loop_end=args.loop_end,
        )


if __name__ == "__main__":
    main()
