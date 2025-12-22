# Tools

Utility scripts for analyzing and debugging elmulti conversions.

## analyze_loops.py

Loop point continuity analyzer for elmulti files. Analyzes WAV files and their corresponding elmulti definitions to check if loop points are seamless.

### Features

- Loop continuity analysis (checks if `samples[loop_end+1] == samples[loop_start]`)
- Single-cycle vs normal loop classification
- Pitch estimation from loop length
- Detailed statistics by category

### Options

| Option | Description |
|--------|-------------|
| `-a, --all` | Analyze all subdirectories |
| `-v, --verbose` | Show detailed per-sample analysis |
| `-p, --pitch` | Show pitch information (frequency, note) |
| `-d, --detailed` | Show detailed summary with single-cycle vs normal breakdown |
| `--sort {name,diff,length}` | Sort results (default: name) |
| `--single-cycle-threshold N` | Max loop length to consider as single-cycle (default: 512) |

### Usage Examples

```bash
# Basic usage - analyze single instrument
python3 tools/analyze_loops.py /path/to/output/InstrumentName

# Analyze all instruments in output directory
python3 tools/analyze_loops.py /path/to/output --all

# Show pitch information
python3 tools/analyze_loops.py /path/to/output --all --pitch

# Detailed summary (single-cycle vs normal loop classification)
python3 tools/analyze_loops.py /path/to/output --all --detailed

# All options combined
python3 tools/analyze_loops.py /path/to/output --all --pitch --detailed

# Sort by loop length
python3 tools/analyze_loops.py /path/to/output --all --sort length

# Sort by diff percentage (worst first)
python3 tools/analyze_loops.py /path/to/output --all --sort diff

# Change single-cycle threshold
python3 tools/analyze_loops.py /path/to/output --all --single-cycle-threshold 256

# Verbose output (per-sample details)
python3 tools/analyze_loops.py /path/to/output --all --verbose
```

### Status Indicators

| Symbol | Status | Description |
|--------|--------|-------------|
| `[✓✓]` | EXCELLENT | diff < 0.1% - Perfect or near-perfect loop |
| `[✓]` | GOOD | diff < 1.0% - Good loop, minor discontinuity |
| `[~]` | FAIR | diff < 5.0% - Noticeable discontinuity |
| `[✗]` | POOR | diff >= 5.0% - Significant discontinuity |
| `[SC]` | Single-cycle | Short loop waveform (pitch priority) |

### Understanding the Output

- **Normal loops** (> threshold samples): Continuity is prioritized. Lower diff% is better.
- **Single-cycle waveforms** (≤ threshold samples): Pitch accuracy is prioritized. Higher diff% is acceptable because exact loop length preservation matters more than seamless transitions.

---

## loop_calculator.py

Interactive calculator for sample rate conversions and loop point calculations. Useful for understanding pitch relationships when working with resampled audio or SFZ files with `transpose` opcodes.

### Features

- Calculate original sample rate from WAV header SR and SFZ `transpose` value
- Compute samples per cycle for any MIDI note at any sample rate
- Calculate pitch error sensitivity (cents per sample)
- Find ideal loop lengths that minimize pitch error
- Convert loop points between sample rates
- Crossfade recommendations for problematic loops

### Modes

| Mode | Usage | Description |
|------|-------|-------------|
| Interactive | `./loop_calculator.py` | Wizard-style prompts for human users |
| CLI | `./loop_calculator.py --wav-sr 66896 ...` | Direct arguments for LLM agents/scripts |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--wav-sr` | (required) | Sample rate from WAV file header (Hz) |
| `--transpose` | 0 | SFZ transpose value in semitones |
| `--target-sr` | 48000 | Target sample rate for conversion (Hz) |
| `--key` | 60 (C3) | Reference MIDI note number for calculations |
| `--loop-start` | - | Loop start point (sample number) |
| `--loop-end` | - | Loop end point (sample number, inclusive) |

### Usage Examples

```bash
# Interactive wizard mode
./loop_calculator.py

# Basic calculation with transpose
./loop_calculator.py --wav-sr 66896 --transpose -24

# Full calculation with loop points
./loop_calculator.py --wav-sr 66896 --transpose -24 --loop-start 4752 --loop-end 4815

# Different target sample rate and reference key
./loop_calculator.py --wav-sr 22050 --target-sr 44100 --key 72

# Show help
./loop_calculator.py --help
```

### Key Formulas

```
Original SR = WAV_SR × 2^(transpose / 12)
Samples per cycle = Sample_Rate / Frequency
1 sample error (cents) = 1200 × log2((samples_per_cycle + 1) / samples_per_cycle)
```

### Background: Why This Tool Exists

Some SF2→SFZ converters (e.g., Polyphone) "bake" root key information into the WAV sample rate. For example, a sample originally recorded at 16,724 Hz might be stored with a header SR of 66,896 Hz and `transpose=-24` to compensate. This tool helps:

1. Reverse-calculate the original sample rate
2. Understand pitch relationships during resampling
3. Find optimal loop lengths that minimize pitch drift
