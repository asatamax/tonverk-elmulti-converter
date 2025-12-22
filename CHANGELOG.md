# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
