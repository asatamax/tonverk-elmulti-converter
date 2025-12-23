# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
