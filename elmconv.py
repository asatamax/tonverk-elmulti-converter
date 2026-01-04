#!/usr/bin/env python3
"""Elektron Tonverk (.elmulti) converter.

Converts EXS24 (and SFZ in future) instruments to Tonverk multi-sample format.

Usage: elmconv.py <input-file> <output-dir> [--resample]

Copyright (c) 2013, vonred (original EXS parsing)
Copyright (c) 2025, elmconv contributors
"""

__version__ = "1.1.3"

import argparse
import glob
import os
import re
import struct
import subprocess
import sys
from collections import defaultdict
from typing import Protocol


# =============================================================================
# Exception Classes
# =============================================================================


class ConversionError(Exception):
    """Raised when conversion fails (missing samples, ffmpeg failure, etc.)."""

    pass


class ValidationError(Exception):
    """Raised when input validation fails (invalid format, name too long, etc.)."""

    pass


class FFmpegNotFoundError(ConversionError):
    """Raised when ffmpeg is not available or missing soxr support."""

    pass


# =============================================================================
# Logging Abstraction
# =============================================================================


class LogCallback(Protocol):
    """Protocol for logging callbacks."""

    def __call__(self, message: str, level: str = "info") -> None: ...


def default_logger(message: str, level: str = "info") -> None:
    """Default CLI logger using print()."""
    if level == "error":
        print(message, file=sys.stderr)
    elif level == "warning":
        print(f"Warning: {message}")
    else:
        print(message)


# =============================================================================
# Constants
# =============================================================================

NOTE_NAMES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]

# Anchor note mapping for thinning (uppercase only, case-sensitive)
ANCHOR_NOTE_MAP = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
    "H": 11,
}

# Name length limits (based on Tonverk Factory Library analysis: max observed = 21 chars)
MAX_NAME_WARN = 24  # Warning threshold: may be truncated on Tonverk display
MAX_NAME_ERROR = 64  # Error threshold: filesystem safety limit

# Characters invalid in filenames (cross-platform)
INVALID_FILENAME_CHARS = r'/\:*?"<>|'

# Common ffmpeg installation paths for packaged apps
# (Packaged .app/.exe don't inherit shell PATH)
FFMPEG_SEARCH_PATHS = {
    "darwin": [  # macOS
        "/opt/homebrew/bin",  # Apple Silicon Homebrew
        "/usr/local/bin",  # Intel Homebrew / manual install
        "/usr/bin",  # System (unlikely but possible)
    ],
    "win32": [  # Windows
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        r"C:\ffmpeg\bin",
        r"C:\tools\ffmpeg\bin",  # Chocolatey
    ],
}

# Cached ffmpeg path (None = not searched, "" = not found, str = found path)
_ffmpeg_path: str | None = None


# =============================================================================
# Loop Point Convention (SFZ/elmulti)
# =============================================================================
#
# SFZ and elmulti use the INCLUSIVE convention for loop points:
#   - loop_start: First sample of the loop (inclusive)
#   - loop_end: Last sample of the loop (inclusive)
#
# Loop length calculation:
#   loop_length = loop_end - loop_start + 1
#
# Playback flow:
#   samples[loop_start] → ... → samples[loop_end] → samples[loop_start] → ...
#
# Example:
#   loop_start = 100, loop_end = 101
#   → Loop plays samples[100] and samples[101] (2 samples)
#   → Loop length = 101 - 100 + 1 = 2
#
# Continuity evaluation strategies:
#   1. Amplitude discontinuity (click minimization):
#      |samples[loop_end] - samples[loop_start]| → minimize
#      Best for: Normal loops where audible clicks are the concern.
#
#   2. Phase coherence (periodicity):
#      |samples[loop_end + 1] - samples[loop_start]| → minimize
#      Best for: Single-cycle waveforms where the loop should represent
#      exactly one period of a periodic signal.
#
# =============================================================================


# =============================================================================
# Conversion Statistics
# =============================================================================


class ConversionStats:
    """Collects statistics and warnings during conversion."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all statistics."""
        # File counts
        self.files_processed = 0

        # Sample counts
        self.total_samples = 0
        self.resampled_samples = 0
        self.normalized_samples = 0

        # Loop counts
        self.loops_with_loop = 0
        self.loops_without_loop = 0
        self.loops_single_cycle = 0
        self.loops_normal = 0
        self.loops_optimized = 0

        # Thinning stats
        self.thin_applied = False
        self.thin_factor = 0
        self.thin_original_pitches = 0
        self.thin_result_pitches = 0
        self.thin_original_interval = 0
        self.thin_result_interval = 0

        # Warnings: list of (filename, message)
        self.warnings = []

    def add_warning(self, filename, message):
        """Add a warning with associated filename."""
        self.warnings.append((filename, message))

    def print_summary(self, settings=None):
        """Print conversion summary."""
        print("\n" + "=" * 50)
        print("CONVERSION SUMMARY")
        print("=" * 50)

        # Settings section
        if settings:
            print("\n--- Settings ---")
            if settings.get("prefix"):
                print(f'Prefix: "{settings["prefix"]}"')
            if settings.get("resample_rate"):
                print(f"Resample rate: {settings['resample_rate']} Hz")
            else:
                print("Resample rate: None (keep original)")
            normalize_db = settings.get("normalize_db")
            if normalize_db is not None:
                print(f"Normalize level: {normalize_db} dB")
            else:
                print("Normalize: Disabled")
            print(f"Round loop points: {'Yes' if settings.get('round_loop') else 'No'}")
            if settings.get("optimize_loops"):
                print(
                    f"Optimize loops: Yes (search range: {settings.get('loop_search_range', 5)})"
                )
            else:
                print("Optimize loops: No")
            sc_threshold = settings.get("single_cycle_threshold", 512)
            if sc_threshold > 0:
                print(f"Single-cycle threshold: {sc_threshold} samples")
            else:
                print("Single-cycle detection: Disabled")
            print(
                f"Embed loop info (smpl): {'Yes' if settings.get('embed_loop', True) else 'No'}"
            )

        # Statistics section
        print("\n--- Statistics ---")
        print(f"Files processed: {self.files_processed}")
        print(f"Total samples: {self.total_samples}", end="")
        extras = []
        if self.resampled_samples > 0:
            extras.append(f"resampled: {self.resampled_samples}")
        if self.normalized_samples > 0:
            extras.append(f"normalized: {self.normalized_samples}")
        if extras:
            print(f" ({', '.join(extras)})")
        else:
            print()

        print("\nLoops:")
        print(f"  With loop: {self.loops_with_loop}")
        if self.loops_with_loop > 0:
            print(f"    - Single-cycle: {self.loops_single_cycle}")
            optimized_info = (
                f" (optimized: {self.loops_optimized})"
                if self.loops_optimized > 0
                else ""
            )
            print(f"    - Normal: {self.loops_normal}{optimized_info}")
        print(f"  Without loop: {self.loops_without_loop}")

        # Thinning section
        if self.thin_applied:
            print("\nThinning:")
            print(f"  Factor: {self.thin_factor} (keep 1 of every {self.thin_factor})")
            reduction_pct = (
                (1 - self.thin_result_pitches / self.thin_original_pitches) * 100
                if self.thin_original_pitches > 0
                else 0
            )
            print(
                f"  Pitches: {self.thin_original_pitches} -> {self.thin_result_pitches} "
                f"({100 - reduction_pct:.0f}% kept)"
            )
            print(
                f"  Interval: {self.thin_original_interval} -> "
                f"{self.thin_result_interval} semitones"
            )

        # Warnings section
        if self.warnings:
            print(f"\n--- Warnings ({len(self.warnings)}) ---")
            for filename, message in self.warnings:
                print(f"  - {filename}: {message}")
        else:
            print("\n--- No warnings ---")

        print("=" * 50)


# Global stats instance
conversion_stats = ConversionStats()


# =============================================================================
# FFmpeg Path Resolution
# =============================================================================


def find_ffmpeg() -> str:
    """Find ffmpeg executable path.

    Searches common installation paths for packaged apps that don't
    inherit shell PATH. Caches the result for performance.

    Returns:
        str: Path to ffmpeg directory (e.g., "/opt/homebrew/bin")
             or empty string if not found.
    """
    global _ffmpeg_path

    # Return cached result
    if _ffmpeg_path is not None:
        return _ffmpeg_path

    # First, check if ffmpeg is already in PATH
    import shutil

    if shutil.which("ffmpeg"):
        _ffmpeg_path = ""  # Empty means use default (in PATH)
        return _ffmpeg_path

    # Search common installation paths
    search_paths = FFMPEG_SEARCH_PATHS.get(sys.platform, [])
    for path in search_paths:
        if sys.platform == "win32":
            ffmpeg_exe = os.path.join(path, "ffmpeg.exe")
        else:
            ffmpeg_exe = os.path.join(path, "ffmpeg")

        if os.path.isfile(ffmpeg_exe) and os.access(ffmpeg_exe, os.X_OK):
            _ffmpeg_path = path
            return _ffmpeg_path

    # Not found
    _ffmpeg_path = ""
    return _ffmpeg_path


def get_ffmpeg_cmd() -> str:
    """Get the ffmpeg command path.

    Returns:
        str: Full path to ffmpeg, or just "ffmpeg" if in PATH.
    """
    path = find_ffmpeg()
    if path:
        if sys.platform == "win32":
            return os.path.join(path, "ffmpeg.exe")
        return os.path.join(path, "ffmpeg")
    return "ffmpeg"


def get_ffprobe_cmd() -> str:
    """Get the ffprobe command path.

    Returns:
        str: Full path to ffprobe, or just "ffprobe" if in PATH.
    """
    path = find_ffmpeg()
    if path:
        if sys.platform == "win32":
            return os.path.join(path, "ffprobe.exe")
        return os.path.join(path, "ffprobe")
    return "ffprobe"


# =============================================================================
# Utility Functions
# =============================================================================


def get_ffmpeg_error_message(ffmpeg_available: bool, soxr_available: bool) -> str:
    """Get user-friendly error message for ffmpeg issues.

    Args:
        ffmpeg_available: Whether ffmpeg binary was found
        soxr_available: Whether soxr resampler is supported

    Returns:
        str: Error message, or empty string if no error
    """
    if not ffmpeg_available:
        return (
            "ffmpeg is not installed.\n\n"
            "Please install ffmpeg:\n\n"
            "macOS:\n"
            "  brew install ffmpeg\n\n"
            "Windows:\n"
            "  1. Download from https://ffmpeg.org/download.html\n"
            "     (Choose 'Windows builds' -> 'full' build)\n"
            "  2. Extract and add bin/ folder to PATH\n\n"
            "Linux:\n"
            "  sudo apt install ffmpeg  (Ubuntu/Debian)\n"
            "  sudo dnf install ffmpeg  (Fedora)"
        )
    if not soxr_available:
        return (
            "ffmpeg is missing soxr resampler support.\n\n"
            "The 'soxr' library is required for high-quality resampling.\n\n"
            "macOS:\n"
            "  brew reinstall ffmpeg\n\n"
            "Windows:\n"
            "  Download the 'full' build (not 'essentials') from:\n"
            "  https://ffmpeg.org/download.html\n\n"
            "Linux:\n"
            "  sudo apt install ffmpeg  (should include soxr)"
        )
    return ""


def check_ffmpeg():
    """Check if ffmpeg is available and has soxr resampler support.

    Returns:
        tuple: (ffmpeg_available, soxr_available)
    """
    try:
        ffmpeg_cmd = get_ffmpeg_cmd()
        result = subprocess.run(
            [ffmpeg_cmd, "-version"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return (False, False)

        # Check if soxr resampler is available (required for high-quality resampling)
        # Look for --enable-libsoxr in the build configuration
        soxr_available = "--enable-libsoxr" in result.stdout

        return (True, soxr_available)
    except FileNotFoundError:
        return (False, False)


def get_sample_rate(filepath):
    """Get sample rate of audio file using ffprobe."""
    try:
        ffprobe_cmd = get_ffprobe_cmd()
        result = subprocess.run(
            [
                ffprobe_cmd,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=sample_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (FileNotFoundError, ValueError):
        pass
    return None


def get_sample_count(filepath):
    """Get total sample count of audio file.

    Tries ffprobe first, falls back to wave module for WAV files.
    """
    # Try ffprobe first
    try:
        ffprobe_cmd = get_ffprobe_cmd()
        result = subprocess.run(
            [
                ffprobe_cmd,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=nb_samples",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except (FileNotFoundError, ValueError):
        pass

    # Fallback to wave module for WAV files
    if filepath.lower().endswith(".wav"):
        try:
            import wave

            with wave.open(filepath, "rb") as w:
                return w.getnframes()
        except Exception:
            pass

    return None


def read_wav_samples(filepath):
    """Read sample data from WAV file.

    Args:
        filepath: Path to WAV file

    Returns:
        list: Sample values as integers
    """
    import wave

    with wave.open(filepath, "rb") as w:
        sampwidth = w.getsampwidth()
        nframes = w.getnframes()
        data = w.readframes(nframes)

        if sampwidth == 3:  # 24-bit
            samples = []
            for i in range(0, len(data), 3):
                b = data[i : i + 3]
                val = int.from_bytes(b, "little", signed=True)
                samples.append(val)
            return samples
        elif sampwidth == 2:  # 16-bit
            fmt = f"<{nframes}h"
            return list(struct.unpack(fmt, data))
        elif sampwidth == 1:  # 8-bit
            fmt = f"<{nframes}b"
            return list(struct.unpack(fmt, data))
    return []


def embed_smpl_chunk(wav_path, loop_start=None, loop_end=None, midi_unity_note=60):
    """Embed smpl chunk with loop and/or root note information into WAV file.

    Args:
        wav_path: Path to WAV file (will be modified in-place)
        loop_start: Loop start point (sample index, inclusive), or None for no loop
        loop_end: Loop end point (sample index, inclusive), or None for no loop
        midi_unity_note: MIDI root note number (default: 60 = C4)

    Returns:
        bool: True if successful, False otherwise

    Note: If loop_start and loop_end are None, only the root note is embedded.
    """
    import tempfile
    import shutil

    try:
        # Read original WAV file
        with open(wav_path, "rb") as f:
            riff = f.read(4)
            if riff != b"RIFF":
                return False

            f.read(4)  # file_size (will recalculate)
            wave_id = f.read(4)
            if wave_id != b"WAVE":
                return False

            # Read all chunks
            chunks = []
            sample_rate = 48000  # default
            while True:
                chunk_id = f.read(4)
                if len(chunk_id) < 4:
                    break
                chunk_size = struct.unpack("<I", f.read(4))[0]
                chunk_data = f.read(chunk_size)
                if chunk_size % 2 == 1:  # padding
                    f.read(1)

                # Skip existing smpl chunk (will be replaced)
                if chunk_id == b"smpl":
                    continue

                # Get sample rate from fmt chunk
                if chunk_id == b"fmt ":
                    sample_rate = struct.unpack("<I", chunk_data[4:8])[0]

                chunks.append((chunk_id, chunk_data))

        # Build smpl chunk
        # https://www.recordingblogs.com/wiki/sample-chunk-of-a-wave-file
        sample_period = int(1e9 / sample_rate)  # nanoseconds

        has_loop = loop_start is not None and loop_end is not None

        smpl_data = struct.pack(
            "<IIIIIIIII",
            0,  # manufacturer
            0,  # product
            sample_period,
            midi_unity_note,
            0,  # midi_pitch_fraction
            0,  # smpte_format
            0,  # smpte_offset
            1 if has_loop else 0,  # num_sample_loops
            0,  # sampler_data
        )

        # Add loop information if provided
        if has_loop:
            smpl_data += struct.pack(
                "<IIIIII",
                0,  # cue_point_id
                0,  # loop_type (0 = forward loop)
                loop_start,
                loop_end,
                0,  # fraction
                0,  # play_count (0 = infinite)
            )

        # Write to temporary file first, then replace
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

            # RIFF header (size placeholder)
            tmp.write(b"RIFF")
            tmp.write(struct.pack("<I", 0))
            tmp.write(b"WAVE")

            # Write original chunks
            for chunk_id, chunk_data in chunks:
                tmp.write(chunk_id)
                tmp.write(struct.pack("<I", len(chunk_data)))
                tmp.write(chunk_data)
                if len(chunk_data) % 2 == 1:
                    tmp.write(b"\x00")

            # Write smpl chunk
            tmp.write(b"smpl")
            tmp.write(struct.pack("<I", len(smpl_data)))
            tmp.write(smpl_data)
            if len(smpl_data) % 2 == 1:
                tmp.write(b"\x00")

            # Update file size
            file_size = tmp.tell() - 8
            tmp.seek(4)
            tmp.write(struct.pack("<I", file_size))

        # Replace original file
        shutil.move(tmp_path, wav_path)
        return True

    except Exception as e:
        print(f"    Warning: Failed to embed smpl chunk: {e}")
        return False


def validate_sample_position(value, sample_count, can_omit=False):
    """Validate sample position against file bounds.

    SFZ and elmulti use inclusive sample positions (0 to sample_count-1).
    Some SF2->SFZ converters incorrectly output exclusive values (sample_count),
    which would cause out-of-bounds errors on Tonverk.

    Args:
        value: Sample position value to validate
        sample_count: Total number of samples in the WAV file
        can_omit: If True, return 0 for out-of-bounds (meaning "omit this field")
                  If False, clamp to max valid value (sample_count - 1)

    Returns:
        tuple: (validated_value, warning_message or None)
    """
    if value <= 0 or sample_count is None or sample_count <= 0:
        return value, None

    max_valid = sample_count - 1  # inclusive: last valid index

    if value >= sample_count:
        if can_omit:
            return 0, f"out of bounds ({value} >= {sample_count}), omitting"
        else:
            return max_valid, f"clamped {value} -> {max_valid}"

    return value, None


def is_single_cycle(loop_length, threshold=512):
    """Determine if a loop is a single-cycle waveform based on loop length.

    Single-cycle waveforms are very short loops that represent a single period
    of a periodic waveform. For these, pitch accuracy is more important than
    loop point continuity optimization.

    Args:
        loop_length: Length of the loop in samples (at output sample rate)
        threshold: Maximum loop length to consider as single-cycle (default: 512)

    Returns:
        bool: True if the loop should be treated as single-cycle
    """
    return loop_length <= threshold


def calculate_single_cycle_loop(
    orig_loop_start, orig_loop_end, resample_ratio, samples=None
):
    """Calculate loop points for single-cycle waveforms with pitch priority.

    For single-cycle waveforms, pitch accuracy is paramount. We scale the
    loop LENGTH (not individual endpoints) to preserve the exact frequency.
    Rounding start and end separately can cause ±1 sample variation in length,
    which translates to significant pitch deviation (~19 cents for 90-sample loops).

    Note: loop_end is INCLUSIVE (SFZ/elmulti convention).

    Args:
        orig_loop_start: Original loop start position
        orig_loop_end: Original loop end position (inclusive)
        resample_ratio: Ratio of new_rate / orig_rate
        samples: Optional sample data for phase coherence check

    Returns:
        tuple: (loop_start, loop_end, warning_message or None)
    """
    # Calculate original loop length (inclusive: +1)
    orig_loop_length = orig_loop_end - orig_loop_start + 1

    # Scale loop length with rounding (pitch priority)
    # Ensure minimum length of 1 to prevent loop_end < loop_start
    new_loop_length = max(1, round(orig_loop_length * resample_ratio))

    # Calculate loop_start position
    loop_start = round(orig_loop_start * resample_ratio)

    # Derive loop_end from loop_start and length (inclusive: -1)
    loop_end = loop_start + new_loop_length - 1

    warnings = []

    # Validate and clamp loop points if samples provided
    if samples:
        total_samples = len(samples)

        # Check and clamp out-of-bounds conditions (safety first)
        if loop_start < 0:
            warnings.append(f"loop_start clamped: {loop_start} -> 0")
            loop_start = 0
            # Recalculate loop_end to maintain loop length
            loop_end = loop_start + new_loop_length - 1

        if loop_start >= total_samples:
            clamped_start = total_samples - 1
            warnings.append(f"loop_start clamped: {loop_start} -> {clamped_start}")
            loop_start = clamped_start

        if loop_end < loop_start:
            # This shouldn't happen with max(1, ...) but guard anyway
            warnings.append(f"loop_end clamped: {loop_end} -> {loop_start}")
            loop_end = loop_start

        if loop_end >= total_samples:
            clamped_end = total_samples - 1
            warnings.append(f"loop_end clamped: {loop_end} -> {clamped_end}")
            loop_end = clamped_end

        # Recalculate actual loop length after clamping
        actual_loop_length = loop_end - loop_start + 1

        # Check phase coherence only if indices are valid and we have room
        if loop_end + 1 < total_samples:
            val_start = samples[loop_start]
            val_end_next = samples[loop_end + 1]
            diff_phase = abs(val_end_next - val_start)

            # Calculate normalized difference (assuming 24-bit audio)
            max_val = 8388607  # 2^23 - 1
            diff_percent = (diff_phase / max_val) * 100

            if diff_percent > 5.0:
                warnings.append(
                    f"phase coherence: diff={diff_percent:.1f}% (loop_len={actual_loop_length})"
                )

    warning = f"Single-cycle loop warning: {'; '.join(warnings)}" if warnings else None

    return loop_start, loop_end, warning


def optimize_loop_points(samples, approx_start, approx_end, search_range=5):
    """Find optimal loop points to minimize amplitude discontinuity (clicks).

    This function optimizes for click minimization by finding loop points where
    samples[loop_end] ≈ samples[loop_start]. This is the amplitude at the
    actual loop boundary during playback.

    Note: loop_end is INCLUSIVE (SFZ/elmulti convention).
    Note: This function should NOT be used for single-cycle waveforms as even
    ±1 sample shift can cause significant pitch deviation.

    Args:
        samples: List of sample values
        approx_start: Approximate loop start position
        approx_end: Approximate loop end position (inclusive)
        search_range: Number of samples to search in each direction

    Returns:
        tuple: (optimal_start, optimal_end, difference)
    """
    best_diff = float("inf")
    best_start = approx_start
    best_end = approx_end

    total_samples = len(samples)

    for s_offset in range(-search_range, search_range + 1):
        for e_offset in range(-search_range, search_range + 1):
            test_start = approx_start + s_offset
            test_end = approx_end + e_offset

            # Validate index bounds
            if test_start < 0 or test_start >= total_samples:
                continue
            if test_end < 0 or test_end >= total_samples:
                continue
            if test_end <= test_start:
                continue

            # Minimize amplitude discontinuity at loop boundary
            # Playback: ... → samples[test_end] → samples[test_start] → ...
            diff = abs(samples[test_end] - samples[test_start])
            if diff < best_diff:
                best_diff = diff
                best_start = test_start
                best_end = test_end

    return best_start, best_end, best_diff


def midi_to_note_name(midi_note):
    """Convert MIDI note number to Tonverk note name (e.g., 60 -> 'c3')."""
    octave = (midi_note // 12) - 2  # Tonverk uses C0 = 24
    note = NOTE_NAMES[midi_note % 12]
    return f"{note}{octave}"


def sanitize_filename(name):
    """Sanitize string for use as filename.

    Args:
        name: String to sanitize

    Returns:
        str: Sanitized filename-safe string
    """
    # Replace invalid characters with underscore
    result = name
    for char in INVALID_FILENAME_CHARS:
        result = result.replace(char, "_")
    # Trim whitespace from ends
    return result.strip()


def validate_name_length(name, prefix=""):
    """Validate instrument name length.

    Based on Tonverk Factory Library analysis (max observed: 21 chars).

    Args:
        name: Instrument name
        prefix: Optional prefix string

    Returns:
        tuple: (is_valid, warning_message or None)

    Raises:
        ValueError: If total length exceeds MAX_NAME_ERROR
    """
    total_len = len(prefix) + len(name)

    if total_len > MAX_NAME_ERROR:
        raise ValueError(
            f"Name too long ({total_len} chars). "
            f"Maximum allowed: {MAX_NAME_ERROR} chars"
        )

    if total_len > MAX_NAME_WARN:
        return True, (
            f"Name length ({total_len} chars) exceeds recommended "
            f"limit of {MAX_NAME_WARN} chars. May be truncated on Tonverk display."
        )

    return True, None


def parse_anchor_note(note_str):
    """Parse anchor note value for thinning (0-11 or note name).

    Args:
        note_str: Note as number (0-11) or name (C, C#, Db, etc.)

    Returns:
        int: Note value 0-11, or None if invalid

    Note names are case-sensitive (uppercase only):
    C, C#, Db, D, D#, Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, B, H
    """
    note_str = str(note_str).strip()

    # Try as integer first
    try:
        val = int(note_str)
        if 0 <= val <= 11:
            return val
        return None
    except ValueError:
        pass

    # Try as note name (uppercase only)
    upper = note_str.upper()
    if upper in ANCHOR_NOTE_MAP:
        return ANCHOR_NOTE_MAP[upper]

    return None


def get_peak_level(filepath):
    """Get peak level of audio file using ffmpeg volumedetect.

    Args:
        filepath: Path to audio file

    Returns:
        float: Peak level in dB (negative value, e.g., -3.5)
               None if detection fails
    """
    try:
        ffmpeg_cmd = get_ffmpeg_cmd()
        result = subprocess.run(
            [ffmpeg_cmd, "-i", filepath, "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        # Parse: max_volume: -3.5 dB
        match = re.search(r"max_volume:\s*([-\d.]+)\s*dB", result.stderr)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


def normalize_audio(filepath, target_db=0.0):
    """Normalize audio file to target peak level.

    Args:
        filepath: Path to WAV file (modified in-place)
        target_db: Target peak level in dB (default: 0.0)

    Returns:
        tuple: (success, gain_applied_db)
    """
    peak = get_peak_level(filepath)
    if peak is None:
        return False, 0.0

    gain = target_db - peak  # e.g., 0 - (-3.5) = +3.5 dB

    if abs(gain) < 0.1:  # Already at target level
        return True, 0.0

    # Apply gain using ffmpeg
    temp_path = filepath + ".tmp.wav"
    try:
        ffmpeg_cmd = get_ffmpeg_cmd()
        result = subprocess.run(
            [
                ffmpeg_cmd,
                "-y",
                "-i",
                filepath,
                "-af",
                f"volume={gain}dB",
                "-acodec",
                "pcm_s24le",
                temp_path,
            ],
            capture_output=True,
        )

        if result.returncode == 0:
            os.replace(temp_path, filepath)
            return True, gain
        else:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, 0.0
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, 0.0


def find_sample_file(sample_name, search_dirs):
    """Find sample file in search directories."""
    for search_dir in search_dirs:
        if not os.path.isdir(search_dir):
            continue

        # Exact match (no listdir needed)
        exact_path = os.path.join(search_dir, sample_name)
        if os.path.isfile(exact_path):
            return exact_path

        # Try to list directory (may fail due to permissions)
        try:
            dir_contents = os.listdir(search_dir)
        except (PermissionError, OSError):
            continue

        # Case-insensitive match
        sample_lower = sample_name.lower()
        for filename in dir_contents:
            if filename.lower() == sample_lower:
                return os.path.join(search_dir, filename)

        # Match by note name pattern
        note_pattern = re.compile(r"-([A-Ga-g][#b]?\d+)-", re.IGNORECASE)
        sample_match = note_pattern.search(sample_name)
        if sample_match:
            sample_note = sample_match.group(1).upper()
            for filename in dir_contents:
                file_match = note_pattern.search(filename)
                if file_match and file_match.group(1).upper() == sample_note:
                    return os.path.join(search_dir, filename)

    return None


def convert_to_wav(source_path, dest_path, target_rate=None):
    """Convert audio file to WAV using ffmpeg.

    Args:
        source_path: Input audio file
        dest_path: Output WAV file
        target_rate: Target sample rate (None = keep original)

    Returns:
        tuple: (success, original_rate, output_rate)
    """
    original_rate = get_sample_rate(source_path)
    if original_rate is None:
        original_rate = 44100  # Fallback

    ffmpeg_cmd = get_ffmpeg_cmd()
    cmd = [ffmpeg_cmd, "-y", "-i", source_path, "-acodec", "pcm_s24le"]

    if target_rate and target_rate != original_rate:
        cmd.extend(["-ar", str(target_rate), "-af", "aresample=resampler=soxr"])
        output_rate = target_rate
    else:
        output_rate = original_rate

    cmd.append(dest_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return (result.returncode == 0, original_rate, output_rate)
    except FileNotFoundError:
        raise FFmpegNotFoundError("ffmpeg not found. Please install ffmpeg.")


# =============================================================================
# EXS24 Parser
# =============================================================================


class EXSChunk:
    """Base class for EXS24 chunks."""

    _size = None

    @classmethod
    def parse(cls, instrument, offset):
        sig = struct.unpack_from("<I", instrument.data, offset)[0]
        for subclass in cls.__subclasses__():
            if subclass.sig is None:
                continue
            if subclass.sig == sig:
                return subclass(instrument, offset)
            if hasattr(subclass, "sig_new") and subclass.sig_new == sig:
                return subclass(instrument, offset)
        return EXSUnknown(instrument, offset)

    @property
    def size(self):
        if self._size is None:
            self._size = (
                84 + struct.unpack_from("<I", self.instrument.data, self.offset + 4)[0]
            )
        return self._size

    @property
    def id(self):
        return struct.unpack_from("<I", self.instrument.data, self.offset + 8)[0]

    @property
    def name(self):
        raw = self.instrument.data[self.offset + 20 : self.offset + 84]
        return raw.decode("utf-8").split("\x00")[0]


class EXSHeader(EXSChunk):
    sig = 0x00000101
    sig_new = 0x40000101

    def __init__(self, instrument, offset):
        self.instrument = instrument
        self.offset = offset


class EXSZone(EXSChunk):
    sig = 0x01000101
    sig_new = 0x41000101

    def __init__(self, instrument, offset):
        self.instrument = instrument
        self.offset = offset

    def _read_byte(self, rel_offset):
        return struct.unpack_from("B", self.instrument.data, self.offset + rel_offset)[
            0
        ]

    def _read_sbyte(self, rel_offset):
        return struct.unpack_from("b", self.instrument.data, self.offset + rel_offset)[
            0
        ]

    def _read_int(self, rel_offset):
        return struct.unpack_from("<i", self.instrument.data, self.offset + rel_offset)[
            0
        ]

    def _read_uint(self, rel_offset):
        return struct.unpack_from("<I", self.instrument.data, self.offset + rel_offset)[
            0
        ]

    @property
    def rootnote(self):
        return self._read_byte(85)

    @property
    def finetune(self):
        return self._read_sbyte(86)

    @property
    def pan(self):
        return self._read_sbyte(87)

    @property
    def volumeadjust(self):
        return self._read_sbyte(88)

    @property
    def startnote(self):
        return self._read_byte(90)

    @property
    def endnote(self):
        return self._read_byte(91)

    @property
    def minvel(self):
        return self._read_byte(93)

    @property
    def maxvel(self):
        return self._read_byte(94)

    @property
    def samplestart(self):
        return self._read_int(96)

    @property
    def sampleend(self):
        return self._read_int(100)

    @property
    def loopstart(self):
        return self._read_int(104)

    @property
    def loopend(self):
        return self._read_int(108)

    @property
    def loopcrossfade(self):
        return self._read_int(112)

    @property
    def loopopts(self):
        return self._read_byte(117)

    @property
    def loop(self):
        return (self.loopopts & 1) != 0

    @property
    def loop_equal_power(self):
        return (self.loopopts & 2) != 0

    @property
    def loop_play_to_end_on_release(self):
        """EXS24: true = stop looping on release. INVERSE of elmulti."""
        return (self.loopopts & 4) != 0

    @property
    def pitchtrack(self):
        return not (self._read_byte(84) & 1)

    @property
    def oneshot(self):
        return self._read_byte(84) & 2

    @property
    def group(self):
        group = self._read_int(172)
        if group >= 0:
            return group
        return len(self.instrument.groups) - 1

    @property
    def sampleindex(self):
        return self._read_uint(176)


class EXSGroup(EXSChunk):
    sig = 0x02000101
    sig_new = 0x42000101

    ENABLE_BY_NONE = 0
    ENABLE_BY_NOTE = 1
    ENABLE_BY_ROUND_ROBIN = 2
    ENABLE_BY_CONTROL = 3
    ENABLE_BY_BEND = 4
    ENABLE_BY_CHANNEL = 5
    ENABLE_BY_ARTICULATION = 6
    ENABLE_BY_TEMPO = 7

    def __init__(self, instrument, offset):
        self.instrument = instrument
        self.offset = offset

    @property
    def polyphony(self):
        return struct.unpack_from("B", self.instrument.data, self.offset + 86)[0]

    @property
    def trigger(self):
        return struct.unpack_from("B", self.instrument.data, self.offset + 157)[0]

    @property
    def output(self):
        return struct.unpack_from("B", self.instrument.data, self.offset + 158)[0]

    @property
    def sequence(self):
        return struct.unpack_from("<i", self.instrument.data, self.offset + 164)[0]

    @property
    def enable_by_type(self):
        try:
            if len(self.instrument.data) > self.offset + 168:
                return struct.unpack_from("B", self.instrument.data, self.offset + 168)[
                    0
                ]
        except Exception:
            pass
        return 0

    @property
    def round_robin_position(self):
        try:
            if len(self.instrument.data) > self.offset + 167:
                return struct.unpack_from(
                    "<i", self.instrument.data, self.offset + 164
                )[0]
        except Exception:
            pass
        return -1

    @property
    def is_round_robin(self):
        return self.enable_by_type == self.ENABLE_BY_ROUND_ROBIN


class EXSSample(EXSChunk):
    sig = 0x03000101
    sig_new = 0x43000101

    def __init__(self, instrument, offset):
        self.instrument = instrument
        self.offset = offset

    @property
    def length(self):
        return struct.unpack_from("<i", self.instrument.data, self.offset + 88)[0]

    @property
    def rate(self):
        return struct.unpack_from("<i", self.instrument.data, self.offset + 92)[0]

    @property
    def bitdepth(self):
        return struct.unpack_from("B", self.instrument.data, self.offset + 96)[0]

    @property
    def file_path(self):
        """Full file path stored in sample chunk (offset 164, 256 bytes)."""
        raw = self.instrument.data[self.offset + 164 : self.offset + 164 + 256]
        return raw.decode("utf-8", errors="ignore").split("\x00")[0]

    @property
    def file_name(self):
        """File name stored in sample chunk (offset 420, 256 bytes)."""
        if len(self.instrument.data) > self.offset + 420:
            raw = self.instrument.data[self.offset + 420 : self.offset + 420 + 256]
            name = raw.decode("utf-8", errors="ignore").split("\x00")[0]
            if name:
                return name
        return self.name  # Fallback to chunk name


class EXSParam(EXSChunk):
    sig = 0x04000101
    sig_new = 0x44000101

    def __init__(self, instrument, offset):
        self.instrument = instrument
        self.offset = offset


class EXSUnknown(EXSChunk):
    sig = None

    def __init__(self, instrument, offset):
        self.instrument = instrument
        self.offset = offset


class EXSInstrument:
    """EXS24 instrument file parser."""

    def __init__(self, exsfile_name):
        self._zones = None
        self._groups = None
        self._samples = None
        self._objects = None
        self.exsfile_name = exsfile_name
        self.data = None

        if os.stat(exsfile_name).st_size > 1024 * 1024:
            raise RuntimeError("EXS file is too large (> 1MB)")

        with open(exsfile_name, "rb") as exsfile:
            self.data = exsfile.read(84)
            sig = struct.unpack_from("<I", self.data, 0)[0]
            if (
                struct.unpack_from(">I", self.data, 0)[0] == EXSHeader.sig
                and self.data[16:20] == b"SOBT"
            ):
                raise RuntimeError("Big endian EXS files are not supported")
            if (
                not (sig == EXSHeader.sig or sig == EXSHeader.sig_new)
                and self.data[16:20] == b"TBOS"
            ):
                raise RuntimeError("Not a valid EXS file")
            self.data += exsfile.read(1024 * 1024 - 84)

    @property
    def objects(self):
        if not self._objects:
            self._objects = []
            offset = 0
            end = len(self.data)
            while offset < end:
                new_object = EXSChunk.parse(self, offset)
                self._objects.append(new_object)
                offset += new_object.size
                if isinstance(new_object, EXSZone):
                    self.zones.append(new_object)
                elif isinstance(new_object, EXSGroup):
                    self.groups.append(new_object)
                elif isinstance(new_object, EXSSample):
                    self.samples.append(new_object)
        return self._objects

    @property
    def zones(self):
        if not self._zones:
            self._zones = []
            len(self.objects)  # trigger parsing
        return self._zones

    @property
    def samples(self):
        if not self._samples:
            self._samples = []
            len(self.objects)
        return self._samples

    @property
    def groups(self):
        if not self._groups:
            self._groups = []
            len(self.objects)
        return self._groups


# =============================================================================
# Zone Data Structure (Intermediate Representation)
# =============================================================================
#
# zone_data is a list of dictionaries with the following keys:
#   - pitch: int (MIDI note number, root note)
#   - minvel: int (0-127)
#   - maxvel: int (0-127)
#   - source_path: str (path to source audio file)
#   - sample_name: str (original sample name)
#   - loop: bool
#   - loop_start: int (samples)
#   - loop_end: int (samples)
#   - loop_crossfade_ms: int (milliseconds, for EXS)
#   - keep_looping_on_release: bool
#   - rr_position: int (-1 if not round-robin)
#   - vel_layer: int (velocity layer index, assigned later)
#   - original_rate: int (original sample rate)
#
# =============================================================================


def parse_exs(exs_path):
    """Parse EXS24 file and return zone data list.

    Args:
        exs_path: Path to EXS24 instrument file

    Returns:
        tuple: (zone_data_list, instrument_name, sample_paths)
    """
    print(f"Loading: {exs_path}")
    exs = EXSInstrument(exs_path)

    exs_dir = os.path.dirname(os.path.abspath(exs_path))
    exs_basename = os.path.splitext(os.path.basename(exs_path))[0]
    instrument_name = exs_basename

    # Find all samples
    print(f"Checking {len(exs.samples)} samples...")
    sample_paths = {}
    missing = []

    for sample in exs.samples:
        found = None

        # 1. Try file_path from EXS (may be absolute or relative)
        if sample.file_path:
            # Normalize Windows-style path separators
            file_path = sample.file_path.replace("\\", "/")
            file_name = (sample.file_name or sample.name).replace("\\", "/")
            # file_path may be directory or full path
            if os.path.isabs(file_path):
                # Try as full file path first
                if os.path.isfile(file_path):
                    found = file_path
                # Try as directory + filename
                elif os.path.isdir(file_path):
                    full_path = os.path.join(file_path, file_name)
                    if os.path.isfile(full_path):
                        found = full_path
            else:
                # Try as relative path from EXS directory
                rel_path = os.path.join(exs_dir, file_path)
                rel_path = os.path.normpath(rel_path)
                if os.path.isfile(rel_path):
                    found = rel_path
                elif os.path.isdir(rel_path):
                    full_path = os.path.join(rel_path, file_name)
                    if os.path.isfile(full_path):
                        found = full_path

        # 2. Fallback: search in common directories by filename
        if not found:
            search_dirs = [
                exs_dir,
                os.path.join(exs_dir, exs_basename),
                os.path.join(exs_dir, "..", exs_basename),
                os.path.join(exs_dir, "..", "Samples", exs_basename),
            ]

            # 3. Extract relative path hints from file_path and search ancestors
            # Many sample libraries store samples in parallel directories like:
            #   LibraryRoot/Logic EXS/... (EXS files)
            #   LibraryRoot/WAV/...       (sample files)
            if sample.file_path:
                fp = sample.file_path.replace("\\", "/")
                path_parts = [p for p in fp.split("/") if p]

                # Try last 1-4 directory components as relative path
                for depth in range(1, min(5, len(path_parts))):
                    rel_subpath = os.path.join(*path_parts[-depth:])

                    # Search from EXS directory upward (up to 6 levels)
                    current_dir = exs_dir
                    for _ in range(6):
                        candidate = os.path.normpath(
                            os.path.join(current_dir, rel_subpath)
                        )
                        if os.path.isdir(candidate) and candidate not in search_dirs:
                            search_dirs.append(candidate)
                        parent = os.path.dirname(current_dir)
                        if parent == current_dir:
                            break
                        current_dir = parent

            file_name = sample.file_name or sample.name
            found = find_sample_file(file_name, search_dirs)

        if found:
            sample_paths[sample.name] = found
            print(f"  [OK] {sample.name}")
        else:
            missing.append(sample.name)
            print(f"  [NG] {sample.name}")
            if sample.file_path:
                print(f"       (file_path: {sample.file_path})")

    if missing:
        missing_list = ", ".join(missing[:5])
        if len(missing) > 5:
            missing_list += f", ... ({len(missing) - 5} more)"
        raise ConversionError(f"{len(missing)} sample(s) not found: {missing_list}")

    # Analyze groups for round-robin
    print(f"\nAnalyzing {len(exs.groups)} groups...")
    for i, group in enumerate(exs.groups):
        if group.is_round_robin:
            print(f"  Group {i}: Round-robin position {group.round_robin_position}")

    # Build zone data
    zone_data = []
    for zone in exs.zones:
        sample = exs.samples[zone.sampleindex]
        sample_name = sample.name
        source_path = sample_paths[sample_name]

        # Get round-robin info from group
        group_idx = zone.group
        rr_position = -1
        if 0 <= group_idx < len(exs.groups):
            group = exs.groups[group_idx]
            if group.is_round_robin:
                rr_position = group.round_robin_position

        zone_data.append(
            {
                "pitch": zone.rootnote,
                "key_center": zone.rootnote,  # EXS has no transpose, key_center = pitch
                "minvel": zone.minvel,
                "maxvel": zone.maxvel,
                "source_path": source_path,
                "sample_name": sample_name,
                "trim_start": zone.samplestart,
                "trim_end": zone.sampleend,
                "loop": zone.loop,
                "loop_start": zone.loopstart,
                "loop_end": zone.loopend,
                "loop_crossfade_ms": zone.loopcrossfade,
                "keep_looping_on_release": not zone.loop_play_to_end_on_release,
                "rr_position": rr_position,
                "original_rate": sample.rate,
            }
        )

    # Sort by pitch, velocity, round-robin position
    zone_data.sort(key=lambda z: (z["pitch"], z["minvel"], z["rr_position"]))

    # Assign velocity layer indices
    vel_layers_by_pitch = defaultdict(list)
    for zd in zone_data:
        pitch = zd["pitch"]
        minvel = zd["minvel"]
        if minvel not in vel_layers_by_pitch[pitch]:
            vel_layers_by_pitch[pitch].append(minvel)

    for pitch in vel_layers_by_pitch:
        vel_layers_by_pitch[pitch].sort()

    for zd in zone_data:
        pitch = zd["pitch"]
        minvel = zd["minvel"]
        zd["vel_layer"] = vel_layers_by_pitch[pitch].index(minvel)

    return zone_data, instrument_name


# =============================================================================
# SFZ Parser
# =============================================================================


def parse_sfz(sfz_path):
    """Parse SFZ file and return zone data list.

    Args:
        sfz_path: Path to SFZ instrument file

    Returns:
        tuple: (zone_data_list, instrument_name)
    """
    print(f"Loading: {sfz_path}")

    sfz_dir = os.path.dirname(os.path.abspath(sfz_path))
    sfz_basename = os.path.splitext(os.path.basename(sfz_path))[0]
    instrument_name = sfz_basename

    # Read and preprocess SFZ file
    with open(sfz_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Remove comments
    content = re.sub(r"//[^\n]*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # Parse headers and opcodes
    # Split by headers while keeping the header names
    header_pattern = re.compile(
        r"<(control|global|master|group|region)>", re.IGNORECASE
    )
    parts = header_pattern.split(content)

    # Build scoped opcode storage
    control_opcodes = {}
    global_opcodes = {}
    master_opcodes = {}
    group_opcodes = {}
    regions = []

    current_header = None
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if header_pattern.match(f"<{part}>"):
            current_header = part.lower()
            i += 1
            if i < len(parts):
                opcodes = parse_sfz_opcodes(parts[i])
                if current_header == "control":
                    control_opcodes = opcodes
                elif current_header == "global":
                    global_opcodes = opcodes
                elif current_header == "master":
                    master_opcodes = opcodes
                elif current_header == "group":
                    group_opcodes = opcodes
                elif current_header == "region":
                    # Merge inherited opcodes
                    merged = {}
                    merged.update(global_opcodes)
                    merged.update(master_opcodes)
                    merged.update(group_opcodes)
                    merged.update(opcodes)
                    regions.append(merged)
        i += 1

    # Get default_path from control (normalize Windows-style paths)
    default_path = control_opcodes.get("default_path", "").replace("\\", "/")

    # Find all samples and build zone data
    print(f"Checking {len(regions)} regions...")
    zone_data = []
    missing = []

    for region in regions:
        sample_opcode = region.get("sample")
        if not sample_opcode:
            continue

        # Normalize Windows-style path separators
        sample_rel = sample_opcode.replace("\\", "/")

        # Resolve sample path
        if default_path:
            sample_rel = os.path.join(default_path, sample_rel)

        # Try as relative path from SFZ directory
        sample_path = os.path.join(sfz_dir, sample_rel)
        sample_path = os.path.normpath(sample_path)

        if not os.path.isfile(sample_path):
            missing.append(sample_rel)
            print(f"  [NG] {sample_rel}")
            print(f"       (sample opcode: {sample_opcode})")
            if default_path:
                print(f"       (default_path: {default_path})")
            print(f"       (resolved to: {sample_path})")
            continue

        print(f"  [OK] {sample_rel}")

        # Get pitch (key or pitch_keycenter)
        pitch = None
        if "pitch_keycenter" in region:
            pitch = parse_sfz_note(region["pitch_keycenter"])
        elif "key" in region:
            pitch = parse_sfz_note(region["key"])

        if pitch is None:
            print(f"  [SKIP] No pitch defined for {sample_rel}")
            continue

        # Get transpose and calculate key_center
        # transpose shifts the playback pitch: negative = lower pitch = slower playback
        # key_center = pitch_keycenter - transpose
        transpose = int(region.get("transpose", 0))
        key_center = pitch - transpose

        # Velocity
        lovel = int(region.get("lovel", 0))
        hivel = int(region.get("hivel", 127))

        # Round-robin
        seq_position = int(region.get("seq_position", -1))
        rr_position = seq_position - 1 if seq_position > 0 else -1

        # Trim (offset/end)
        trim_start = int(region.get("offset", 0))
        trim_end = int(region.get("end", 0))

        # Loop settings
        loop_mode = region.get("loop_mode", region.get("loopmode", "no_loop"))
        loop = loop_mode in ("loop_sustain", "loop_continuous")

        loop_start = int(region.get("loop_start", region.get("loopstart", 0)))
        loop_end = int(region.get("loop_end", region.get("loopend", 0)))

        # loop_crossfade is in seconds, convert to ms
        loop_crossfade_sec = float(region.get("loop_crossfade", 0))
        loop_crossfade_ms = int(loop_crossfade_sec * 1000)

        # keep_looping_on_release
        keep_looping = loop_mode == "loop_continuous"

        # Get sample rate from file
        original_rate = get_sample_rate(sample_path) or 44100

        zone_data.append(
            {
                "pitch": pitch,
                "key_center": key_center,
                "minvel": lovel,
                "maxvel": hivel,
                "source_path": sample_path,
                "sample_name": os.path.basename(sample_rel),
                "trim_start": trim_start,
                "trim_end": trim_end,
                "loop": loop,
                "loop_start": loop_start,
                "loop_end": loop_end,
                "loop_crossfade_ms": loop_crossfade_ms,
                "keep_looping_on_release": keep_looping,
                "rr_position": rr_position,
                "original_rate": original_rate,
            }
        )

    if missing:
        missing_list = ", ".join(missing[:5])
        if len(missing) > 5:
            missing_list += f", ... ({len(missing) - 5} more)"
        raise ConversionError(f"{len(missing)} sample(s) not found: {missing_list}")

    # Sort by pitch, velocity, round-robin position
    zone_data.sort(key=lambda z: (z["pitch"], z["minvel"], z["rr_position"]))

    # Assign velocity layer indices
    vel_layers_by_pitch = defaultdict(list)
    for zd in zone_data:
        pitch = zd["pitch"]
        minvel = zd["minvel"]
        if minvel not in vel_layers_by_pitch[pitch]:
            vel_layers_by_pitch[pitch].append(minvel)

    for pitch in vel_layers_by_pitch:
        vel_layers_by_pitch[pitch].sort()

    for zd in zone_data:
        pitch = zd["pitch"]
        minvel = zd["minvel"]
        zd["vel_layer"] = vel_layers_by_pitch[pitch].index(minvel)

    print(f"\nParsed {len(zone_data)} zones")
    return zone_data, instrument_name


def parse_sfz_opcodes(text):
    """Parse SFZ opcodes from text block.

    Args:
        text: Text containing opcode=value pairs

    Returns:
        dict: Opcode name to value mapping
    """
    opcodes = {}
    # Match opcode=value, handling spaces in sample paths
    # Opcodes end at next opcode or end of string
    pattern = re.compile(r"(\w+)=([^=]+?)(?=\s+\w+=|$)", re.DOTALL)

    for match in pattern.finditer(text):
        key = match.group(1).lower()
        value = match.group(2).strip()
        opcodes[key] = value

    return opcodes


def parse_sfz_note(note_str):
    """Parse SFZ note value (MIDI number or IPN notation).

    Args:
        note_str: Note as MIDI number (e.g., "60") or IPN (e.g., "C4")

    Returns:
        int: MIDI note number, or None if invalid
    """
    note_str = str(note_str).strip()

    # Try as integer first
    try:
        return int(note_str)
    except ValueError:
        pass

    # Parse IPN notation (e.g., C4, F#3, Bb2)
    match = re.match(r"([A-Ga-g])([#b]?)(-?\d+)", note_str)
    if match:
        note_name = match.group(1).upper()
        accidental = match.group(2)
        octave = int(match.group(3))

        note_map = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        midi = note_map[note_name] + (octave + 1) * 12

        if accidental == "#":
            midi += 1
        elif accidental == "b":
            midi -= 1

        return midi

    return None


# =============================================================================
# Sample Thinning
# =============================================================================


def analyze_sample_map(zone_data):
    """Analyze sample map for thinning preview and validation.

    Args:
        zone_data: List of zone data dictionaries

    Returns:
        dict: Analysis results with keys:
            - unique_pitches: sorted list of unique MIDI pitches
            - pitch_count: number of unique pitches
            - zone_count: total number of zones
            - interval: most common interval between adjacent pitches (mode)
            - pitch_range: (min_pitch, max_pitch) tuple
            - velocity_layers: number of velocity layers (estimated)
            - has_round_robin: whether round-robin samples exist
    """
    if not zone_data:
        return {
            "unique_pitches": [],
            "pitch_count": 0,
            "zone_count": 0,
            "interval": 0,
            "pitch_range": (0, 0),
            "velocity_layers": 0,
            "has_round_robin": False,
        }

    unique_pitches = sorted(set(zd["pitch"] for zd in zone_data))
    pitch_count = len(unique_pitches)

    # Calculate most common interval (mode)
    if pitch_count >= 2:
        intervals = [
            unique_pitches[i + 1] - unique_pitches[i] for i in range(pitch_count - 1)
        ]
        interval = max(set(intervals), key=intervals.count)
    else:
        interval = 0

    # Estimate velocity layers (max layers at any pitch)
    vel_layers_by_pitch = {}
    for zd in zone_data:
        pitch = zd["pitch"]
        minvel = zd["minvel"]
        if pitch not in vel_layers_by_pitch:
            vel_layers_by_pitch[pitch] = set()
        vel_layers_by_pitch[pitch].add(minvel)
    velocity_layers = max(len(v) for v in vel_layers_by_pitch.values())

    # Check for round-robin
    has_round_robin = any(zd["rr_position"] >= 0 for zd in zone_data)

    return {
        "unique_pitches": unique_pitches,
        "pitch_count": pitch_count,
        "zone_count": len(zone_data),
        "interval": interval,
        "pitch_range": (min(unique_pitches), max(unique_pitches)),
        "velocity_layers": velocity_layers,
        "has_round_robin": has_round_robin,
    }


def apply_thinning(zone_data, thin_factor, anchor=0, max_interval=None):
    """Apply thinning to zone data by keeping every Nth pitch.

    Args:
        zone_data: List of zone data dictionaries
        thin_factor: Keep 1 of every N samples (N >= 2)
        anchor: Base note for selection (0-11, default: 0 = C)
        max_interval: Maximum allowed interval in result (optional)

    Returns:
        tuple: (thinned_zone_data, stats_dict)

    Raises:
        ValidationError: If thin_factor < 2 or max_interval constraint violated
    """
    if thin_factor < 2:
        raise ValidationError("--thin value must be >= 2")

    analysis = analyze_sample_map(zone_data)
    unique_pitches = analysis["unique_pitches"]
    original_interval = analysis["interval"]

    if len(unique_pitches) < 2:
        # Nothing to thin
        return zone_data, {
            "original_pitches": len(unique_pitches),
            "result_pitches": len(unique_pitches),
            "removed_pitches": 0,
            "original_interval": original_interval,
            "result_interval": original_interval,
            "original_zones": len(zone_data),
            "result_zones": len(zone_data),
            "anchor": anchor,
            "selected_pitches": unique_pitches,
        }

    # Calculate resulting interval
    result_interval = original_interval * thin_factor

    # Validate max_interval constraint (prevent over-thinning)
    if max_interval is not None:
        if result_interval > max_interval:
            raise ValidationError(
                f"Thinning would result in {result_interval}-semitone intervals, "
                f"but --thin-max-interval limits to {max_interval} semitones.\n"
                f"Suggestion: Use --thin {max_interval // original_interval} or lower."
            )

    # Find starting index based on anchor
    # Look for the first pitch whose pitch class matches anchor
    start_idx = 0
    for i, pitch in enumerate(unique_pitches):
        if pitch % 12 == anchor:
            start_idx = i
            break
    else:
        # No exact match, find closest pitch class to anchor
        min_dist = 12
        for i, pitch in enumerate(unique_pitches):
            dist = min((pitch % 12 - anchor) % 12, (anchor - pitch % 12) % 12)
            if dist < min_dist:
                min_dist = dist
                start_idx = i

    # Select every Nth pitch bidirectionally from start_idx
    selected_pitches = set()

    # Forward selection
    for i in range(start_idx, len(unique_pitches), thin_factor):
        selected_pitches.add(unique_pitches[i])

    # Backward selection
    for i in range(start_idx - thin_factor, -1, -thin_factor):
        selected_pitches.add(unique_pitches[i])

    # Filter zone_data to keep only zones with selected pitches
    thinned_data = [zd for zd in zone_data if zd["pitch"] in selected_pitches]

    stats = {
        "original_pitches": len(unique_pitches),
        "result_pitches": len(selected_pitches),
        "removed_pitches": len(unique_pitches) - len(selected_pitches),
        "original_interval": original_interval,
        "result_interval": result_interval,
        "original_zones": len(zone_data),
        "result_zones": len(thinned_data),
        "anchor": anchor,
        "selected_pitches": sorted(selected_pitches),
    }

    return thinned_data, stats


def print_thin_preview(zone_data, thin_factor, anchor=0, max_interval=None):
    """Print preview of thinning operation without converting.

    Args:
        zone_data: Original zone data list
        thin_factor: Thinning factor (N)
        anchor: Anchor note (0-11)
        max_interval: Maximum interval constraint

    Raises:
        ValidationError: If thinning constraints are violated
    """
    print("\n" + "=" * 60)
    print("THINNING PREVIEW")
    print("=" * 60)

    analysis = analyze_sample_map(zone_data)

    print("\nInput Analysis:")
    print(f"  Total zones: {analysis['zone_count']}")
    print(f"  Unique pitches: {analysis['pitch_count']}")
    print(f"  Current interval: {analysis['interval']} semitones")
    if analysis["pitch_count"] > 0:
        min_p, max_p = analysis["pitch_range"]
        print(
            f"  Pitch range: {midi_to_note_name(min_p).upper()} - "
            f"{midi_to_note_name(max_p).upper()} (MIDI {min_p}-{max_p})"
        )
    print(f"  Velocity layers: {analysis['velocity_layers']}")
    if analysis["has_round_robin"]:
        print("  Round-robin: Yes")

    print("\nThinning Settings:")
    print(f"  Factor: {thin_factor} (keep 1 of every {thin_factor})")
    anchor_name = NOTE_NAMES[anchor].upper()
    print(f"  Anchor: {anchor} ({anchor_name})")
    if max_interval is not None:
        print(f"  Max interval: {max_interval} semitones")

    # Apply thinning to get stats (may raise ValidationError)
    _, stats = apply_thinning(zone_data, thin_factor, anchor, max_interval)

    reduction_pct = (
        (1 - stats["result_pitches"] / stats["original_pitches"]) * 100
        if stats["original_pitches"] > 0
        else 0
    )

    print("\nResult:")
    print(
        f"  Remaining pitches: {stats['result_pitches']} "
        f"({100 - reduction_pct:.0f}% of original)"
    )
    print(f"  Removed pitches: {stats['removed_pitches']}")
    print(f"  Remaining zones: {stats['result_zones']}")
    print(
        f"  Result interval: {stats['result_interval']} semitones "
        f"(was {stats['original_interval']})"
    )

    # Show selected pitches
    print("\nPitches to keep:")
    pitch_names = [
        f"  {p:3d} ({midi_to_note_name(p).upper()})" for p in stats["selected_pitches"]
    ]
    # Show first 20 and last 5 if too many
    if len(pitch_names) > 25:
        for name in pitch_names[:20]:
            print(name)
        print(f"  ... ({len(pitch_names) - 25} more)")
        for name in pitch_names[-5:]:
            print(name)
    else:
        for name in pitch_names:
            print(name)

    print("\n" + "=" * 60)
    print("Preview complete. Run without --thin-preview to convert.")
    print("=" * 60)


def write_elmulti(
    zone_data,
    output_dir,
    instrument_name,
    target_rate=None,
    round_loop_points=False,
    accurate_ratio=False,
    optimize_loops=False,
    loop_search_range=5,
    single_cycle_threshold=512,
    embed_loop=True,
    prefix="",
    normalize_db=None,
):
    """Convert zone data to elmulti format with WAV files.

    Args:
        zone_data: List of zone data dictionaries
        output_dir: Output directory
        instrument_name: Name for the instrument
        target_rate: Target sample rate (None = keep original)
        round_loop_points: Use round() instead of int() for loop point calculation
        accurate_ratio: Calculate resample ratio from actual output file length
        optimize_loops: Optimize loop points after resampling for seamless loops
        loop_search_range: Number of samples to search in each direction
        single_cycle_threshold: Max loop length to treat as single-cycle (0 to disable)
        embed_loop: Embed loop info (smpl chunk) into WAV files (default: True)
        prefix: Prefix to add to instrument name and filenames (default: "")
        normalize_db: Target peak level for normalization in dB (None = disabled)

    Returns:
        dict: Summary statistics
    """
    # Apply prefix to instrument name
    prefixed_name = f"{prefix}{instrument_name}" if prefix else instrument_name
    # Sanitize for use in filenames
    safe_name = sanitize_filename(prefixed_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput: {output_dir}")

    if target_rate:
        print(f"\nConverting samples to WAV (resampling to {target_rate} Hz)...")
    else:
        print("\nConverting samples to WAV...")

    sample_counter = defaultdict(int)
    resampled_count = 0

    # Convert samples and update zone_data with output info
    for zd in zone_data:
        pitch = zd["pitch"]
        vel_layer = zd["vel_layer"]
        note_name = midi_to_note_name(pitch)

        # Handle round-robin suffix
        base_key = (pitch, vel_layer)
        rr_suffix = ""
        if zd["rr_position"] >= 0:
            rr_suffix = f"-rr{zd['rr_position']}"
        elif sample_counter[base_key] > 0:
            rr_suffix = f"-rr{sample_counter[base_key]}"
        sample_counter[base_key] += 1

        new_filename = (
            f"{safe_name}-{vel_layer:03d}-{pitch:03d}-{note_name}{rr_suffix}.wav"
        )
        dest_path = os.path.join(output_dir, new_filename)

        if not os.path.exists(dest_path):
            success, original_rate, output_rate = convert_to_wav(
                zd["source_path"], dest_path, target_rate
            )
            if success:
                conversion_stats.total_samples += 1
                if original_rate != output_rate:
                    print(
                        f"  Resampled: {new_filename} ({original_rate} -> {output_rate} Hz)"
                    )
                    resampled_count += 1
                    conversion_stats.resampled_samples += 1
                else:
                    print(f"  Converted: {new_filename}")
            else:
                raise ConversionError(f"Failed to convert: {zd['source_path']}")

            # Calculate resample ratio
            if accurate_ratio and original_rate != output_rate:
                # Use actual file lengths for more accurate ratio
                original_samples = get_sample_count(zd["source_path"])
                output_samples = get_sample_count(dest_path)
                if original_samples and output_samples and original_samples > 0:
                    zd["resample_ratio"] = output_samples / original_samples
                else:
                    # Fallback to theoretical ratio
                    zd["resample_ratio"] = output_rate / original_rate
            else:
                # Use theoretical ratio (sample rate based)
                zd["resample_ratio"] = output_rate / original_rate
            zd["output_rate"] = output_rate
        else:
            print(f"  Exists: {new_filename}")
            zd["resample_ratio"] = 1.0
            zd["output_rate"] = target_rate if target_rate else zd["original_rate"]
            conversion_stats.total_samples += 1

        zd["new_filename"] = new_filename

    # Normalize samples if requested (must happen BEFORE loop processing)
    if normalize_db is not None:
        print(f"\nNormalizing samples to {normalize_db} dB...")
        for zd in zone_data:
            wav_path = os.path.join(output_dir, zd["new_filename"])
            success, gain = normalize_audio(wav_path, normalize_db)
            if success and abs(gain) > 0.1:
                print(f"  Normalized: {zd['new_filename']} ({gain:+.1f} dB)")
                conversion_stats.normalized_samples += 1
            elif not success:
                print(f"  Warning: Failed to normalize {zd['new_filename']}")
                conversion_stats.add_warning(zd["new_filename"], "normalization failed")

    # Generate .elmulti file
    elmulti_path = os.path.join(output_dir, f"{safe_name}.elmulti")
    print(f"\nGenerating: {safe_name}.elmulti")

    # Group zones by (pitch, minvel)
    zones_by_key = defaultdict(list)
    for zd in zone_data:
        key = (zd["pitch"], zd["minvel"])
        zones_by_key[key].append(zd)

    sorted_keys = sorted(zones_by_key.keys())
    written_pitches = set()

    with open(elmulti_path, "w", newline="\n") as f:
        f.write("# ELEKTRON MULTI-SAMPLE MAPPING FORMAT\n")
        f.write("version = 0\n")
        f.write(f"name = '{prefixed_name}'\n")

        for pitch, minvel in sorted_keys:
            zones_in_key = zones_by_key[(pitch, minvel)]

            # Write key-zone header once per pitch
            if pitch not in written_pitches:
                # Get key_center from the first zone at this pitch
                key_center = zones_in_key[0].get("key_center", pitch)
                f.write("\n[[key-zones]]\n")
                f.write(f"pitch = {pitch}\n")
                f.write(f"key-center = {float(key_center)}\n")
                written_pitches.add(pitch)

            # Velocity layer
            velocity = minvel / 127.0 if minvel > 0 else 0.49411765
            f.write("\n[[key-zones.velocity-layers]]\n")
            f.write(f"velocity = {velocity}\n")
            f.write("strategy = 'Forward'\n")

            # Sample slots (multiple for round-robin)
            for zd in zones_in_key:
                resample_ratio = zd.get("resample_ratio", 1.0)
                output_rate = zd.get("output_rate", 48000)

                f.write("\n[[key-zones.velocity-layers.sample-slots]]\n")
                f.write(f"sample = '{zd['new_filename']}'\n")

                # Trim points (only if > 0)
                # Use int() by default, round() with --round-loop-points option
                convert_func = round if round_loop_points else int
                trim_start = zd.get("trim_start", 0)
                trim_end = zd.get("trim_end", 0)

                # Get actual sample count for validation
                wav_path = os.path.join(output_dir, zd["new_filename"])
                actual_sample_count = get_sample_count(wav_path)

                if trim_start > 0:
                    f.write(
                        f"trim-start = {convert_func(trim_start * resample_ratio)}\n"
                    )
                if trim_end > 0:
                    # Validate trim-end: omit if out of bounds (file uses full length)
                    scaled_trim_end = convert_func(trim_end * resample_ratio)
                    validated_trim_end, trim_warning = validate_sample_position(
                        scaled_trim_end, actual_sample_count, can_omit=True
                    )
                    if trim_warning:
                        print(f"    trim-end {trim_warning}")
                        conversion_stats.add_warning(
                            zd["new_filename"], f"trim-end {trim_warning}"
                        )
                    if validated_trim_end > 0:
                        f.write(f"trim-end = {validated_trim_end}\n")

                if zd["loop"]:
                    f.write("loop-mode = 'Forward'\n")
                    conversion_stats.loops_with_loop += 1

                    # Calculate approximate loop length to determine processing mode
                    # Note: loop_end is INCLUSIVE, so length = end - start + 1
                    approx_loop_length = round(
                        (zd["loop_end"] - zd["loop_start"] + 1) * resample_ratio
                    )

                    # Check if this is a single-cycle waveform
                    is_sc = (
                        single_cycle_threshold > 0
                        and resample_ratio != 1.0
                        and is_single_cycle(approx_loop_length, single_cycle_threshold)
                    )

                    if is_sc:
                        # Single-cycle: use strict ratio calculation (pitch priority)
                        conversion_stats.loops_single_cycle += 1
                        wav_path = os.path.join(output_dir, zd["new_filename"])
                        samples = None
                        try:
                            samples = read_wav_samples(wav_path)
                        except Exception:
                            pass

                        loop_start, loop_end, warning = calculate_single_cycle_loop(
                            zd["loop_start"],
                            zd["loop_end"],
                            resample_ratio,
                            samples,
                        )
                        print(
                            f"    Single-cycle detected: loop_len={approx_loop_length}, "
                            f"using strict ratio"
                        )
                        if warning:
                            print(f"    {warning}")
                            conversion_stats.add_warning(
                                zd["new_filename"], "single-cycle warning"
                            )
                    else:
                        # Normal loop: use standard calculation
                        conversion_stats.loops_normal += 1
                        loop_start = convert_func(zd["loop_start"] * resample_ratio)
                        loop_end = convert_func(zd["loop_end"] * resample_ratio)

                        # Optimize loop points if requested (for normal loops only)
                        # Goal: minimize amplitude discontinuity (clicks) at loop boundary
                        if optimize_loops and resample_ratio != 1.0:
                            wav_path = os.path.join(output_dir, zd["new_filename"])
                            try:
                                samples = read_wav_samples(wav_path)
                                total_samples = len(samples) if samples else 0
                                # Validate both loop_start and loop_end bounds
                                if (
                                    samples
                                    and 0 <= loop_start < total_samples
                                    and 0 <= loop_end < total_samples
                                ):
                                    # Amplitude discontinuity at loop boundary
                                    # Playback: ... → samples[loop_end] → samples[loop_start] → ...
                                    orig_diff = abs(
                                        samples[loop_end] - samples[loop_start]
                                    )
                                    opt_start, opt_end, opt_diff = optimize_loop_points(
                                        samples,
                                        loop_start,
                                        loop_end,
                                        loop_search_range,
                                    )
                                    if opt_diff < orig_diff:
                                        print(
                                            f"    Loop optimized: ({loop_start}, {loop_end}) -> "
                                            f"({opt_start}, {opt_end}), diff: {orig_diff:,} -> {opt_diff:,}"
                                        )
                                        loop_start = opt_start
                                        loop_end = opt_end
                                        conversion_stats.loops_optimized += 1

                                # Clamp loop points to valid range (safety)
                                if loop_start < 0 or loop_start >= total_samples:
                                    clamped = max(0, min(loop_start, total_samples - 1))
                                    print(
                                        f"    Warning: loop_start clamped: {loop_start} -> {clamped}"
                                    )
                                    conversion_stats.add_warning(
                                        zd["new_filename"], "loop_start clamped"
                                    )
                                    loop_start = clamped
                                if loop_end < loop_start:
                                    print(
                                        f"    Warning: loop_end clamped: {loop_end} -> {loop_start}"
                                    )
                                    conversion_stats.add_warning(
                                        zd["new_filename"], "loop_end clamped"
                                    )
                                    loop_end = loop_start
                                if loop_end >= total_samples:
                                    clamped = total_samples - 1
                                    print(
                                        f"    Warning: loop_end clamped: {loop_end} -> {clamped}"
                                    )
                                    conversion_stats.add_warning(
                                        zd["new_filename"], "loop_end clamped"
                                    )
                                    loop_end = clamped
                            except Exception as e:
                                print(f"    Warning: Loop optimization failed: {e}")
                                conversion_stats.add_warning(
                                    zd["new_filename"], "loop optimization failed"
                                )

                    # Validate loop-end: clamp if out of bounds (required field, cannot omit)
                    validated_loop_end, loop_end_warning = validate_sample_position(
                        loop_end, actual_sample_count, can_omit=False
                    )
                    if loop_end_warning:
                        print(f"    loop-end {loop_end_warning}")
                        conversion_stats.add_warning(
                            zd["new_filename"], f"loop-end {loop_end_warning}"
                        )
                        loop_end = validated_loop_end

                    f.write(f"loop-start = {loop_start}\n")
                    f.write(f"loop-end = {loop_end}\n")

                    # Embed smpl chunk into WAV file
                    if embed_loop:
                        wav_path = os.path.join(output_dir, zd["new_filename"])
                        key_center = zd.get("key_center", pitch)
                        if embed_smpl_chunk(wav_path, loop_start, loop_end, key_center):
                            print(f"    Embedded smpl chunk: {zd['new_filename']}")

                    if zd["loop_crossfade_ms"] > 0:
                        crossfade_samples = zd["loop_crossfade_ms"] * (
                            output_rate // 1000
                        )
                        f.write(f"loop-crossfade = {crossfade_samples}\n")

                    if zd["keep_looping_on_release"]:
                        f.write("keep-looping-on-release = true\n")
                else:
                    f.write("loop-mode = 'Off'\n")
                    conversion_stats.loops_without_loop += 1

                    # Embed smpl chunk with root note info (no loop)
                    if embed_loop:
                        wav_path = os.path.join(output_dir, zd["new_filename"])
                        key_center = zd.get("key_center", pitch)
                        if embed_smpl_chunk(wav_path, None, None, key_center):
                            print(
                                f"    Embedded smpl chunk (root note): {zd['new_filename']}"
                            )

    # Increment files processed count
    conversion_stats.files_processed += 1

    # Calculate statistics
    vel_layers_by_pitch = defaultdict(set)
    for zd in zone_data:
        vel_layers_by_pitch[zd["pitch"]].add(zd["minvel"])
    num_vel_layers = sum(len(v) for v in vel_layers_by_pitch.values())
    num_rr = sum(1 for zd in zone_data if zd["rr_position"] >= 0)

    return {
        "num_samples": len(zone_data),
        "num_key_zones": len(written_pitches),
        "num_vel_layers": num_vel_layers,
        "num_rr": num_rr,
        "resampled_count": resampled_count,
        "target_rate": target_rate,
    }


def convert_to_elmulti(
    input_path,
    output_dir,
    target_rate=None,
    round_loop_points=False,
    accurate_ratio=False,
    optimize_loops=False,
    loop_search_range=5,
    single_cycle_threshold=512,
    embed_loop=True,
    prefix="",
    normalize_db=None,
    thin_factor=None,
    thin_anchor=0,
    thin_max_interval=None,
):
    """Convert input file to elmulti format.

    Args:
        input_path: Path to input file (EXS24 or SFZ)
        output_dir: Output directory
        target_rate: Target sample rate for resampling
        round_loop_points: Use round() instead of int() for loop point calculation
        accurate_ratio: Calculate resample ratio from actual output file length
        optimize_loops: Optimize loop points after resampling for seamless loops
        loop_search_range: Number of samples to search in each direction
        single_cycle_threshold: Max loop length to treat as single-cycle (0 to disable)
        embed_loop: Embed loop info (smpl chunk) into WAV files (default: True)
        prefix: Prefix to add to instrument name and filenames (default: "")
        normalize_db: Target peak level for normalization in dB (None = disabled)
        thin_factor: Thinning factor N (keep 1 of every N, None = disabled)
        thin_anchor: Anchor note for thinning (0-11, default: 0 = C)
        thin_max_interval: Maximum interval limit for thinning (optional)
    """
    ext = os.path.splitext(input_path)[1].lower()

    if ext == ".exs":
        zone_data, instrument_name = parse_exs(input_path)
    elif ext == ".sfz":
        zone_data, instrument_name = parse_sfz(input_path)
    else:
        raise ValidationError(f"Unsupported file format: {ext}. Supported: .exs, .sfz")

    # Apply thinning if requested
    if thin_factor is not None:
        zone_data, thin_stats = apply_thinning(
            zone_data, thin_factor, thin_anchor, thin_max_interval
        )
        # Update global stats
        conversion_stats.thin_applied = True
        conversion_stats.thin_factor = thin_factor
        conversion_stats.thin_original_pitches = thin_stats["original_pitches"]
        conversion_stats.thin_result_pitches = thin_stats["result_pitches"]
        conversion_stats.thin_original_interval = thin_stats["original_interval"]
        conversion_stats.thin_result_interval = thin_stats["result_interval"]

        print(
            f"\nThinning applied: {thin_stats['original_pitches']} -> "
            f"{thin_stats['result_pitches']} pitches "
            f"(interval: {thin_stats['original_interval']} -> "
            f"{thin_stats['result_interval']} semitones)"
        )

    # Validate name length (with prefix)
    try:
        _, name_warning = validate_name_length(instrument_name, prefix)
        if name_warning:
            print(f"Warning: {name_warning}")
    except ValueError as e:
        raise ValidationError(str(e))

    # Apply prefix and sanitize for directory name
    prefixed_name = f"{prefix}{instrument_name}" if prefix else instrument_name
    safe_name = sanitize_filename(prefixed_name)

    # Create subdirectory with instrument name (including prefix)
    output_dir = os.path.join(output_dir, safe_name)

    stats = write_elmulti(
        zone_data,
        output_dir,
        instrument_name,
        target_rate,
        round_loop_points,
        accurate_ratio,
        optimize_loops,
        loop_search_range,
        single_cycle_threshold,
        embed_loop,
        prefix,
        normalize_db,
    )

    # Print summary
    print("\n=== Complete ===")
    print(f"Output: {output_dir}")
    print(f"  - {safe_name}.elmulti")
    print(f"  - {stats['num_samples']} WAV files")
    print(f"  - {stats['num_key_zones']} key zones")
    print(f"  - {stats['num_vel_layers']} velocity layers total")
    if stats["num_rr"] > 0:
        print(f"  - {stats['num_rr']} round-robin samples detected")
    if stats["resampled_count"] > 0:
        print(f"  - {stats['resampled_count']} samples resampled to {target_rate} Hz")

    return conversion_stats


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Convert EXS24/SFZ instruments to Elektron Tonverk format.",
        epilog="Outputs .elmulti file and WAV samples in a flat folder.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "input_paths",
        metavar="INPUT_FILE",
        nargs="+",
        help="Path to input file(s) (.exs or .sfz) - supports glob patterns and multiple files",
    )
    parser.add_argument(
        "output_dir",
        metavar="OUTPUT_DIR",
        help="Output directory for .elmulti and WAV files",
    )
    parser.add_argument(
        "--resample-rate",
        "-R",
        type=int,
        default=48000,
        metavar="RATE",
        help="Resample to specified rate in Hz (default: 48000)",
    )
    parser.add_argument(
        "--no-resample",
        action="store_true",
        help="Keep original sample rate (disable resampling to 48kHz)",
    )
    parser.add_argument(
        "--round-loop",
        action="store_true",
        help="Use round() instead of int() for loop point calculation after resampling",
    )
    parser.add_argument(
        "--use-accurate-ratio",
        action="store_true",
        help="Calculate resample ratio from actual output file length instead of sample rates",
    )
    parser.add_argument(
        "--optimize-loop",
        "-O",
        action="store_true",
        help="Optimize loop points after resampling for seamless loops",
    )
    parser.add_argument(
        "--loop-search-range",
        type=int,
        default=5,
        metavar="N",
        help="Number of samples to search in each direction for loop optimization (default: 5)",
    )
    parser.add_argument(
        "--single-cycle-threshold",
        type=int,
        default=512,
        metavar="N",
        help="Max loop length (samples) to treat as single-cycle waveform (default: 512, 0 to disable)",
    )
    parser.add_argument(
        "--no-single-cycle",
        action="store_true",
        help="Disable single-cycle waveform detection",
    )
    parser.add_argument(
        "--no-embed-loop",
        action="store_true",
        help="Do not embed loop info (smpl chunk) into WAV files",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        metavar="PREFIX",
        help="Add prefix to instrument name and filenames (e.g., 'JV1010 - ')",
    )
    parser.add_argument(
        "--normalize",
        "-N",
        nargs="?",
        const=0.0,
        type=float,
        default=None,
        metavar="DB",
        help="Peak normalize WAV files to specified dB level (default: 0dB if flag used)",
    )

    # Thinning options
    parser.add_argument(
        "--thin",
        "-T",
        type=int,
        metavar="N",
        help="Keep 1 of every N samples (reduce to 1/N). Example: --thin 3 keeps C, D#, F#, A",
    )
    parser.add_argument(
        "--thin-preview",
        action="store_true",
        help="Show what --thin would do without converting",
    )
    parser.add_argument(
        "--thin-max-interval",
        type=int,
        metavar="N",
        help="Limit maximum interval to N semitones (prevent over-thinning)",
    )
    parser.add_argument(
        "--thin-anchor",
        type=str,
        metavar="NOTE",
        help="Base note for thinning selection (0-11 or C, C#, Db, D, etc.)",
    )

    args = parser.parse_args()

    try:
        # Check ffmpeg
        ffmpeg_available, soxr_available = check_ffmpeg()
        error_message = get_ffmpeg_error_message(ffmpeg_available, soxr_available)
        if error_message:
            raise FFmpegNotFoundError(error_message)

        # Collect input files (handle both shell-expanded and glob patterns)
        input_files = []
        for path in args.input_paths:
            # Skip if output_dir accidentally got included as input
            # (can happen with certain shell expansions or user error)
            if path == args.output_dir:
                continue
            # Try glob expansion first
            expanded = glob.glob(path)
            if expanded:
                input_files.extend(expanded)
            elif os.path.isfile(path):
                input_files.append(path)
            else:
                # Distinguish between glob pattern with no matches vs non-existent file
                if any(c in path for c in "*?[]"):
                    print(f"Warning: No files matched pattern: {path}")
                else:
                    print(f"Warning: File not found: {path}")

        if not input_files:
            raise ValidationError("No input files found")

        # Check output directory is not a file
        if os.path.isfile(args.output_dir):
            raise ValidationError(
                f"OUTPUT_DIR is a file, not a directory: {args.output_dir}"
            )

        # Sort files for consistent ordering
        input_files.sort()

        # Determine single-cycle threshold (0 if disabled)
        sc_threshold = 0 if args.no_single_cycle else args.single_cycle_threshold

        # Determine resample rate (None if disabled)
        resample_rate = None if args.no_resample else args.resample_rate

        # Validate and parse thinning options
        thin_anchor = 0
        if args.thin_preview and not args.thin:
            raise ValidationError("--thin-preview requires --thin to be specified")
        if args.thin_max_interval is not None and not args.thin:
            raise ValidationError("--thin-max-interval requires --thin to be specified")
        if args.thin_anchor is not None:
            if not args.thin:
                raise ValidationError("--thin-anchor requires --thin to be specified")
            thin_anchor = parse_anchor_note(args.thin_anchor)
            if thin_anchor is None:
                raise ValidationError(
                    f"Invalid anchor note: {args.thin_anchor}. "
                    "Use 0-11 or note names: C, C#, Db, D, D#, Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, B, H"
                )
        if args.thin is not None and args.thin < 2:
            raise ValidationError("--thin value must be >= 2")

        # Handle --thin-preview mode
        if args.thin_preview:
            for input_file in input_files:
                ext = os.path.splitext(input_file)[1].lower()
                if ext == ".exs":
                    zone_data, _ = parse_exs(input_file)
                elif ext == ".sfz":
                    zone_data, _ = parse_sfz(input_file)
                else:
                    raise ValidationError(
                        f"Unsupported file format: {ext}. Supported: .exs, .sfz"
                    )
                print_thin_preview(
                    zone_data, args.thin, thin_anchor, args.thin_max_interval
                )
            return  # Exit without conversion

        # Reset stats before conversion
        conversion_stats.reset()

        # Run conversion for each file
        print(f"Found {len(input_files)} file(s) to convert\n")
        for i, input_file in enumerate(input_files, 1):
            if len(input_files) > 1:
                print(f"{'=' * 60}")
                print(f"[{i}/{len(input_files)}] {os.path.basename(input_file)}")
                print(f"{'=' * 60}")

            convert_to_elmulti(
                input_file,
                args.output_dir,
                resample_rate,
                args.round_loop,
                args.use_accurate_ratio,
                args.optimize_loop,
                args.loop_search_range,
                sc_threshold,
                not args.no_embed_loop,
                args.prefix,
                args.normalize,
                args.thin,
                thin_anchor,
                args.thin_max_interval,
            )
            if len(input_files) > 1:
                print()

        # Print conversion summary
        settings = {
            "prefix": args.prefix,
            "resample_rate": resample_rate,
            "normalize_db": args.normalize,
            "round_loop": args.round_loop,
            "optimize_loops": args.optimize_loop,
            "loop_search_range": args.loop_search_range,
            "single_cycle_threshold": sc_threshold,
            "embed_loop": not args.no_embed_loop,
        }
        conversion_stats.print_summary(settings)

    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ConversionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
