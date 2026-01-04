# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-01-05

### Added

- **Package installation support** - Install via `uv tool` or `pipx`
  - `uv tool install git+https://github.com/asatamax/tonverk-elmulti-converter` (CLI only)
  - `uv tool install 'elmconv[gui] @ git+...'` (CLI + GUI)
  - Provides `elmconv` and `elmconv-gui` commands after installation
  - Easy upgrades with `uv tool upgrade elmconv`
- **pyproject.toml** - Standard Python packaging configuration
  - Optional `[gui]` extras for GUI dependencies

### Fixed

- **Velocity layer calculation** - Fixed incorrect velocity for zones with minvel=0
  - Previously set to ~0.49 (vel 63) instead of 0.0
  - This caused velocity layers to be misordered in elmulti output

## [1.1.4] - 2026-01-04

### Fixed

- **Windows**: Hide console windows during ffmpeg/ffprobe execution
  - Previously, each subprocess call opened a visible DOS window
  - Now uses `CREATE_NO_WINDOW` flag on Windows for silent operation

## [1.1.3] - 2026-01-04

### Added

- **Sample thinning** - Reduce sample count by keeping every Nth pitch
  - `--thin N` - Keep 1 of every N samples (reduce to 1/N)
  - `--thin-preview` - Preview thinning results without converting
  - `--thin-max-interval N` - Limit maximum interval to prevent over-thinning
  - `--thin-anchor NOTE` - Base note for selection (0-11 or C, C#, Db, etc.)
- **GUI**: Thinning options (Factor, Max Interval, Anchor Note)

### Fixed

- **smpl chunk embedding** - Now embeds root note info for ALL samples, not just looped ones
  - Fixes pitch mapping issues on Tonverk for non-looped samples

## [1.1.1] - 2026-01-04

### Added

- **GUI**: Remember last directory in file pickers during session
- **GUI**: Show elmconv version in startup log

### Fixed

- **EXS**: Improved sample search for relocated libraries
  - Add ancestor directory search using `file_path` hints from EXS metadata
  - Supports common library layouts where samples are in parallel folders (e.g., `Logic EXS/` vs `WAV/`)
  - Add PermissionError/OSError handling in sample search
  - Cache `os.listdir()` results to avoid redundant calls
- **SFZ**: Enhanced error output with original opcode, default_path, and resolved path

## [1.1.0] - 2026-01-03

### Added

- **Flet-based GUI** for cross-platform graphical interface
  - Output folder selection with empty folder warning
  - Options: Resample 48kHz, Optimize loops, Normalize, Prefix
  - File(s) or Folder input selection
  - Conversion log with Copy and Copy Debug buttons
  - Completion dialog with result summary
- `README-GUI.md` with installation and usage instructions
- GitHub Actions workflow for automated builds on release tags
  - Builds for macOS (Apple Silicon, Intel) and Windows

### Changed

- Refactored `elmconv.py` for GUI compatibility
  - Added exception classes: `ConversionError`, `ValidationError`, `FFmpegNotFoundError`
  - Added `check_ffmpeg_for_gui()` for GUI-friendly error messages
  - Improved ffmpeg error messages with OS-specific installation instructions

## [1.0.4] - 2025-12-23

### Changed

- **Resampling to 48kHz is now enabled by default**
  - Tonverk operates at 48kHz/24bit, so converting to 48kHz upfront ensures optimal compatibility
  - Previously required `-R` flag; now automatic
- Added `--no-resample` option to keep original sample rate when needed
- Simplified CLI: removed `nargs="?"` from `--resample-rate`, now takes direct value

### Migration

If you were running without `-R` and want to preserve that behavior:
```bash
# Old (v1.0.3): no resampling by default
elmconv input.exs output/

# New (v1.0.4): use --no-resample to disable
elmconv --no-resample input.exs output/
```

## [1.0.3] - 2025-12-23

### Added

- `--prefix` option to add prefix to instrument name and filenames
  - Use case: Organize converted instruments by source (e.g., `--prefix "JV1010 - "`)
  - Applied to: directory name, WAV filenames, .elmulti filename, and `name` field inside elmulti
- `--normalize` / `-N` option for peak normalization of WAV files
  - Default: 0dB when flag is used without value
  - Supports custom dB level (e.g., `--normalize -1.0`)
  - Normalization occurs before loop processing to ensure sample data consistency
- Name length validation based on Tonverk Factory Library analysis
  - Warning when name exceeds 24 characters (may be truncated on Tonverk display)
  - Error when name exceeds 64 characters (filesystem safety limit)
- `sanitize_filename()` helper function for cross-platform filename safety
- `validate_name_length()` helper function for name length checking
- `get_peak_level()` and `normalize_audio()` helper functions for normalization
- Constants: `MAX_NAME_WARN`, `MAX_NAME_ERROR`, `INVALID_FILENAME_CHARS`

### Changed

- Updated docs/ELMULTI_FORMAT_SPEC.md with Name Length Limits section

## [1.0.2] - 2025-12-22

### Fixed

- Fixed out-of-bounds sample position validation for `trim-end` and `loop-end`
  - Some SF2->SFZ converters output `end` values using exclusive convention (end=sample_count) instead of SFZ's inclusive specification (end=sample_count-1)
  - `trim-end`: Now omitted when >= sample count (file uses full length anyway)
  - `loop-end`: Now clamped to sample_count-1 when out of bounds
- Fixed `get_sample_count()` to use wave module fallback when ffprobe doesn't return `nb_samples`

### Added

- `validate_sample_position()` helper function for bounds checking with clear warning messages

## [1.0.1] - 2025-12-22

### Fixed

- EXS parser now correctly handles Windows-style path separators (backslashes) in sample paths
- Added check for ffmpeg soxr resampler support at startup, with clear error message for Windows users using the "essentials" build

### Changed

- README now notes that Windows users need the "full" ffmpeg build, not "essentials"

## [1.0.0] - 2025-12-21

### Added

- Initial release
- EXS24 (.exs) format support
- SFZ (.sfz) format support
- Velocity layers
- Round-robin samples
- Loop points with crossfade
- Loop point optimization after resampling
- Single-cycle waveform detection for pitch accuracy
- smpl chunk embedding into WAV files
- High-quality resampling using SoX Resampler (soxr)
- SFZ transpose support (key-center adjustment)
