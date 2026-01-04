🇬🇧 English | 🇯🇵 [日本語](README_ja.md)

# elmconv

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-green.svg)](LICENSE)
[![Changelog](https://img.shields.io/badge/changelog-v1.2.0-orange.svg)](CHANGELOG.md)

Convert your multi-sample instruments to Elektron Tonverk.

- ✓ **Logic Pro** — Auto Sampler exports (EXS24)
- ✓ **SFZ libraries** — Use your existing collection
- ✓ **Full-featured** — Loops with crossfade, velocity layers, round-robin

Output: `.elmulti` (Tonverk's native multi-sample format)

**[GUI version available](README-GUI.md)** - No command line required!

## Quick Start

```bash
# Convert an instrument (automatically resamples to 48kHz for Tonverk)
python3 elmconv.py MyInstrument.exs output/
```

## Installation

### Option 1: uv tool / pipx (Recommended)

Install as a command-line tool with automatic dependency management:

```bash
# Using uv (CLI only)
uv tool install git+https://github.com/asatamax/tonverk-elmulti-converter

# Using uv (CLI + GUI)
uv tool install 'elmconv[gui] @ git+https://github.com/asatamax/tonverk-elmulti-converter'

# Using pipx (CLI only)
pipx install git+https://github.com/asatamax/tonverk-elmulti-converter

# Using pipx (CLI + GUI)
pipx install 'elmconv[gui] @ git+https://github.com/asatamax/tonverk-elmulti-converter'
```

After installation:
```bash
elmconv MyInstrument.exs output/      # CLI
elmconv-gui                           # GUI (if installed with [gui])
```

To upgrade:
```bash
uv tool upgrade elmconv
# or
pipx upgrade elmconv
```

### Option 2: Download GUI App

Download pre-built binaries from [GitHub Releases](https://github.com/asatamax/tonverk-elmulti-converter/releases) - no installation required!

### Option 3: Run from Source

```bash
git clone https://github.com/asatamax/tonverk-elmulti-converter.git
cd tonverk-elmulti-converter
python3 elmconv.py MyInstrument.exs output/
```

## Requirements

- Python 3.10+
- ffmpeg

### Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Note: Use the "full" build, not "essentials" (soxr resampler required)
```

## Usage

```bash
python3 elmconv.py INPUT_FILE [INPUT_FILE ...] OUTPUT_DIR [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-N, --normalize [DB]` | Peak normalize WAV files (default: 0dB) |
| `-O, --optimize-loop` | Optimize loop points after resampling for seamless loops |
| `--loop-search-range N` | Search range for loop optimization (default: 5 samples) |
| `--single-cycle-threshold N` | Max loop length to treat as single-cycle (default: 512, 0 to disable) |
| `--no-single-cycle` | Disable single-cycle waveform detection |
| `--no-embed-loop` | Do not embed loop info (smpl chunk) into WAV files |
| `--round-loop` | Use round() instead of int() for loop point calculation |
| `-R, --resample-rate RATE` | Resample to specified rate (default: 48000 Hz) |
| `--no-resample` | Keep original sample rate (disable 48kHz resampling) |
| `--use-accurate-ratio` | Calculate resample ratio from actual file length |
| `--prefix PREFIX` | Add prefix to instrument name and filenames |
| `-T, --thin N` | Keep 1 of every N samples (reduce to 1/N) |
| `--thin-preview` | Show what --thin would do without converting |
| `--thin-max-interval N` | Limit maximum interval to N semitones (prevent over-thinning) |
| `--thin-anchor NOTE` | Base note for thinning selection (0-11 or C, C#, Db, etc.) |

### Examples

```bash
# Basic conversion (resamples to 48kHz by default)
python3 elmconv.py MyInstrument.exs output/

# With loop optimization (recommended for looped samples)
python3 elmconv.py MyInstrument.sfz output/ -O

# Convert multiple files at once
python3 elmconv.py /path/to/*.sfz output/ -O

# Add prefix for organization (e.g., by source)
python3 elmconv.py MyInstrument.exs output/ -O --prefix "JV1010 - "

# Normalize volume levels
python3 elmconv.py MyInstrument.sfz output/ -O --normalize

# Full options: loop optimization, prefix, normalize
python3 elmconv.py MyInstrument.exs output/ -O --prefix "JV1010 - " -N

# Keep original sample rate (disable resampling)
python3 elmconv.py MyInstrument.exs output/ --no-resample

# Custom sample rate
python3 elmconv.py MyInstrument.exs output/ -R 44100

# Thin samples: keep 1 of every 3 (chromatic → C, D#, F#, A)
python3 elmconv.py MyInstrument.exs output/ --thin 3

# Preview thinning without converting
python3 elmconv.py MyInstrument.exs output/ --thin 3 --thin-preview

# Thin with safety limit (max 6 semitone interval)
python3 elmconv.py MyInstrument.exs output/ --thin 3 --thin-max-interval 6
```

### Output

The converter creates a subdirectory for each instrument containing:
- `InstrumentName.elmulti` - Tonverk mapping file
- `*.wav` - Converted samples (24-bit PCM)

## Features

- Velocity layers
- Round-robin samples
- Loop points with crossfade
- **Loop point optimization** - Automatically adjusts loop points after resampling for seamless loops
- **Single-cycle waveform detection** - Preserves pitch accuracy for short loops (synth waveforms)
- **smpl chunk embedding** - Embeds loop info and key-center into WAV files (enabled by default)
- **Sample thinning** - Reduce sample count by keeping every Nth sample (e.g., chromatic → major 3rd intervals)
- High-quality resampling (SoX Resampler)
- SFZ transpose support (key-center adjustment)

## Sample Thinning

Reduce sample count by keeping every Nth pitch. Useful when you have more samples than needed.

- `--thin 3` on chromatic → C, D#, F#, A (major 3rd intervals)
- `--thin 3` on 1 sample/octave → 1 sample per 3 octaves
- Use `--thin-anchor A` to start selection from A
- Use `--thin-max-interval 6` to prevent over-thinning

## Supported Formats

| Format | Status |
|--------|--------|
| EXS24 (.exs) | Supported |
| SFZ (.sfz) | Supported |

## Limitations

The `.elmulti` format has some limitations compared to EXS24/SFZ:

- **Velocity crossfade** - Not supported (hard switch only)
- **Explicit key ranges** - Not supported (Tonverk auto-interpolates between pitches)
- **Sample layering** - Cannot layer multiple samples on same note
- **Ping-pong loops** - Forward loop only
- **Fine tuning / Pan** - Not supported in elmulti format

## Documentation

See the `docs/` directory for detailed format specifications:

- [ELMULTI_FORMAT_SPEC.md](docs/ELMULTI_FORMAT_SPEC.md) - Reverse-engineered `.elmulti` format specification
- [EXS24_FORMAT_SPEC.md](docs/EXS24_FORMAT_SPEC.md) - EXS24 binary format reference
- [FORMAT_MAPPING.md](docs/FORMAT_MAPPING.md) - Field mapping between formats

## Tools

Additional utilities in `tools/`:

- **analyze_loops.py** - Analyze loop point continuity in converted instruments
- **loop_calculator.py** - Calculate sample rate conversions and optimal loop points

See [tools/README.md](tools/README.md) for detailed usage.

## Contributing

Issues and pull requests are welcome! If you encounter any problems or have suggestions, please open an issue.

## License

ISC License - See [LICENSE](LICENSE) file.

Based on [exs2sfz.py](https://gist.github.com/vonred/3965972) by vonred.

## Acknowledgments

- vonred - Original EXS24 parser
- [ConvertWithMoss](https://github.com/git-moss/ConvertWithMoss) - EXS24 format reference
