# elmconv

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-green.svg)](LICENSE)

Convert EXS24 and SFZ instruments to Elektron Tonverk `.elmulti` format.

## Quick Start

```bash
# Most common usage: convert with resampling and loop optimization
python3 elmconv.py MyInstrument.exs output/ -R -O
```

## Requirements

- Python 3.8+
- ffmpeg

### Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Usage

```bash
python3 elmconv.py INPUT_FILE [INPUT_FILE ...] OUTPUT_DIR [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-R, --resample-rate [RATE]` | Resample to specified rate (default: 48000 Hz) |
| `-O, --optimize-loop` | Optimize loop points after resampling for seamless loops |
| `--loop-search-range N` | Search range for loop optimization (default: 5 samples) |
| `--single-cycle-threshold N` | Max loop length to treat as single-cycle (default: 512, 0 to disable) |
| `--no-single-cycle` | Disable single-cycle waveform detection |
| `--no-embed-loop` | Do not embed loop info (smpl chunk) into WAV files |
| `--round-loop` | Use round() instead of int() for loop point calculation |
| `--use-accurate-ratio` | Calculate resample ratio from actual file length |

### Examples

```bash
# Basic conversion (keeps original sample rate)
python3 elmconv.py MyInstrument.exs output/

# Resample to 48kHz (recommended for Tonverk)
python3 elmconv.py MyInstrument.exs output/ --resample-rate

# Resample to specific rate
python3 elmconv.py MyInstrument.exs output/ --resample-rate 44100

# Convert multiple SFZ files at once
python3 elmconv.py /path/to/*.sfz output/

# Resample with loop optimization (recommended)
python3 elmconv.py MyInstrument.sfz output/ -R -O

# Increase search range for problematic loops
python3 elmconv.py MyInstrument.sfz output/ -R -O --loop-search-range 10

# Disable single-cycle detection (treat all loops as normal)
python3 elmconv.py MyInstrument.sfz output/ -R -O --no-single-cycle

# Adjust single-cycle threshold (default: 512 samples)
python3 elmconv.py MyInstrument.sfz output/ -R -O --single-cycle-threshold 256

# Fine-tune loop point calculation (for problematic samples)
python3 elmconv.py MyInstrument.sfz output/ -R --round-loop
python3 elmconv.py MyInstrument.sfz output/ -R --use-accurate-ratio
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
- High-quality resampling (SoX Resampler)
- SFZ transpose support (key-center adjustment)

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
