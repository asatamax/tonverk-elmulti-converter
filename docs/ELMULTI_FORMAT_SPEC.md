# Elektron Tonverk Multi-Sample Format (.elmulti) Specification

Version: 1.4
Last Updated: 2025-12-15
Status: Reverse-engineered from Tonverk Factory Library (112 elmulti + 81 eldrum files analyzed)

## Overview

The `.elmulti` format is Elektron's proprietary multi-sample mapping format used by the Tonverk synthesizer. It defines how WAV sample files are mapped across the keyboard with support for velocity layers, round-robin, and loop parameters.

### Related Format: .eldrum

The `.eldrum` format (for Drum Sets / Subtracks) uses a **similar structure** with a different header comment and typically fewer features:

| Format | Header | Use Case |
|--------|--------|----------|
| `.elmulti` | `# ELEKTRON MULTI-SAMPLE MAPPING FORMAT` | Multi-sampled instruments |
| `.eldrum` | `# ELEKTRON DRUM SET MAPPING FORMAT` | Drum sets, Subtracks |

**Key differences between formats:**

| Feature | `.elmulti` | `.eldrum` |
|---------|-----------|----------|
| `loop-mode` | Common | Typically omitted |
| `loop-start` / `loop-end` | Common | Not used |
| `loop-crossfade` | Common | Not used |
| `keep-looping-on-release` | Optional | Not used |
| `trim-start` / `trim-end` | Optional | Not used |
| Sample filename convention | With MIDI note/octave | Free-form names |

Both formats support velocity layers and round-robin (multiple sample-slots).

## File Format

### Encoding
- Plain text (UTF-8)
- TOML-like syntax
- Line endings: Unix (LF) or Windows (CRLF)

### Basic Structure

```toml
# ELEKTRON MULTI-SAMPLE MAPPING FORMAT
version = 0
name = 'Instrument Name'

[[key-zones]]
# ... key zone definitions
```

## Header

| Field | Type | Description |
|-------|------|-------------|
| `version` | Integer | Format version. Currently always `0` |
| `name` | String | Instrument display name (single or double quotes) |

**Note:** Both quote styles are valid: `name = 'My Instrument'` or `name = "My Instrument"`

## Key Zones

Each `[[key-zones]]` block defines a keyboard region mapped to one or more samples.

```toml
[[key-zones]]
pitch = 60
key-center = 60.0
```

| Field | Type | Description |
|-------|------|-------------|
| `pitch` | Integer | MIDI note number (0-127). Defines the root note for this zone |
| `key-center` | Float | Pitch center for transposition. Usually equals `pitch` as float |

### Note Mapping Convention

#### elmulti File Naming Convention

For sample file names in elmulti, Elektron uses:

**Formula:** `octave = (midi_note // 12) - 2`

| MIDI Note | elmulti File Name | Calculation |
|-----------|-------------------|-------------|
| 12 | c-1 | (12÷12)-2 = -1 |
| 24 | c0 | (24÷12)-2 = 0 |
| 36 | c1 | (36÷12)-2 = 1 |
| 48 | c2 | (48÷12)-2 = 2 |
| 60 | c3 | (60÷12)-2 = 3 |
| 72 | c4 | (72÷12)-2 = 4 |
| 84 | c5 | (84÷12)-2 = 5 |
| 96 | c6 | (96÷12)-2 = 6 |

Note names use lowercase with `#` for sharps and `b` for B natural:
- `c`, `c#`, `d`, `d#`, `e`, `f`, `f#`, `g`, `g#`, `a`, `a#`, `b`

#### SFZ IPN (International Pitch Notation) Convention

**Important:** SFZ files use IPN standard notation, which is different:

**Formula:** `octave = (midi_note // 12) - 1`

| MIDI Note | SFZ (IPN) | elmulti |
|-----------|-----------|---------|
| 60 | C4 | c3 |
| 48 | C3 | c2 |
| 36 | C2 | c1 |
| 24 | C1 | c0 |

Per Tonverk official manual: "MIDI note 0 is called C-1 (and consequently, middle C is C4)"

**Both notations refer to the same MIDI note number.** The difference is only in the display convention.

**Note:** Some Waveforms presets in the factory library use a different octave convention (`octave = midi_note // 12`), resulting in MIDI 60 = c5. This appears to be an inconsistency.

## Velocity Layers

Each key zone contains one or more velocity layers.

```toml
[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'
```

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `velocity` | Float | 0.0 - 1.0 | Velocity threshold. Sample plays when input velocity >= this value |
| `strategy` | String | `'Forward'` | Round-robin playback strategy |

### Velocity Value Reference

Common velocity thresholds observed in factory presets (32 unique values found):

| Float Value | Approximate MIDI (0-127) | Description |
|-------------|-------------------------|-------------|
| 0.06666667 | ~8 | Extremely soft |
| 0.078431375 | ~10 | Very soft |
| 0.24313726 | ~31 | Soft |
| 0.24705882 | ~31 | Soft (drum default) |
| 0.40784314 | ~52 | Medium-soft |
| 0.49411765 | ~63 | Medium (default) |
| 0.5803922 | ~74 | Medium-hard |
| 0.74509805 | ~95 | Hard |
| 0.9098039 | ~116 | Very hard |
| 0.99607850 | ~126 | Maximum |

**Note:** Velocity values follow the pattern `midi_velocity / 127.0`. The slight variations (e.g., 0.24313726 vs 0.24705882) represent different MIDI values (31 vs 31.4).

### Velocity Layer Behavior

**Important**: elmulti uses **hard switching** between velocity layers (no crossfade). When input velocity crosses a threshold, the sample switches immediately to the next layer.

This differs from SFZ format which supports velocity crossfade via `xfin_lovel/hivel` and `xfout_lovel/hivel` parameters.

### Multiple Velocity Layers Example

```toml
[[key-zones]]
pitch = 60
key-center = 60.0

[[key-zones.velocity-layers]]
velocity = 0.078431375
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Piano-000-060-c3.wav'
loop-mode = 'Off'

[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Piano-001-060-c3.wav'
loop-mode = 'Off'

[[key-zones.velocity-layers]]
velocity = 0.9098039
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Piano-002-060-c3.wav'
loop-mode = 'Off'
```

## Sample Slots

Each velocity layer contains one or more sample slots.

```toml
[[key-zones.velocity-layers.sample-slots]]
sample = 'InstrumentName-000-060-c3.wav'
loop-mode = 'Forward'
loop-start = 12345
loop-end = 67890
loop-crossfade = 500
keep-looping-on-release = true
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sample` | String | Yes | Filename (relative path, same directory) |
| `loop-mode` | String | No | Loop behavior (default: one-shot if omitted) |
| `loop-start` | Integer | If looping | Loop start point in samples |
| `loop-end` | Integer | If looping | Loop end point in samples |
| `loop-crossfade` | Integer | No | Crossfade length in samples |
| `keep-looping-on-release` | Boolean | No | Continue looping after key release (used for waveforms) |
| `trim-start` | Integer | No | Sample start position within WAV file (for single-file multi-sample) |
| `trim-end` | Integer | No | Sample end position within WAV file (for single-file multi-sample) |

**Note:** In `.eldrum` files, typically only `sample` is specified, with all loop parameters omitted.

### Single-File Multi-Sample Mode

When using Tonverk's built-in auto-sampling, all samples are stored in a single WAV file. Each sample slot references the same file with different `trim-start` and `trim-end` positions:

```toml
[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument.wav'
trim-start = 1116
trim-end = 219484

[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument.wav'
trim-start = 219484
trim-end = 438364
```

This mode is typically created by the Tonverk hardware. When converting from EXS24, use separate WAV files instead.

### Loop Modes

| Value | Description |
|-------|-------------|
| `'Forward'` | Forward looping enabled |
| `'Off'` | No looping (one-shot) |

### Round-Robin (Multiple Sample Slots)

Multiple `[[key-zones.velocity-layers.sample-slots]]` under the same velocity layer create round-robin variations:

```toml
[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument-000-060-c3.wav'
loop-mode = 'Forward'
loop-start = 1000
loop-end = 5000

[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument-001-060-c3.wav'
loop-mode = 'Forward'
loop-start = 1100
loop-end = 5100

[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument-002-060-c3.wav'
loop-mode = 'Forward'
loop-start = 1050
loop-end = 5050
```

## File Naming Convention

WAV files follow this naming pattern:

```
{InstrumentName}-{VelocityLayer}-{MIDINote}-{NoteName}.wav
```

| Component | Format | Example |
|-----------|--------|---------|
| InstrumentName | String | `Piano`, `Dark Choir` |
| VelocityLayer | 3-digit zero-padded | `000`, `001`, `002` |
| MIDINote | 3-digit zero-padded | `024`, `060`, `095` |
| NoteName | Lowercase with octave | `c0`, `f#3`, `b5` |

### Examples

```
Dark Choir-000-024-c0.wav      # Velocity layer 0, MIDI 24, C0
Piano-002-060-c3.wav           # Velocity layer 2, MIDI 60, C3
Bass-000-036-c1.wav            # Velocity layer 0, MIDI 36, C1
Synth-001-066-f#3.wav          # Velocity layer 1, MIDI 66, F#3
Submarine-000-013-c#-1.wav     # Velocity layer 0, MIDI 13, C#-1 (negative octave)
```

### Drum File Naming (.eldrum)

Drum files typically use descriptive names without MIDI note information:
```
1_Kick_DrumSetName.wav
2_Snare_DrumSetName.wav
3_Tom_DrumSetName.wav
6_ClosedHat_DrumSetName.wav
```

## Audio File Requirements

| Property | Requirement |
|----------|-------------|
| Format | WAV (RIFF) |
| Bit Depth | 16-bit or 24-bit PCM |
| Sample Rate | 48000 Hz recommended |
| Channels | Mono or Stereo |

## Directory Structure

All files must be in a flat directory structure:

```
InstrumentName/
├── InstrumentName.elmulti
├── InstrumentName-000-024-c0.wav
├── InstrumentName-000-036-c1.wav
├── InstrumentName-000-048-c2.wav
└── ...
```

## Complete Example

```toml
# ELEKTRON MULTI-SAMPLE MAPPING FORMAT
version = 0
name = 'Example Pad'

[[key-zones]]
pitch = 36
key-center = 36.0

[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Example Pad-000-036-c1.wav'
loop-mode = 'Forward'
loop-start = 48000
loop-end = 192000
loop-crossfade = 500

[[key-zones]]
pitch = 48
key-center = 48.0

[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Example Pad-000-048-c2.wav'
loop-mode = 'Forward'
loop-start = 48000
loop-end = 180000
loop-crossfade = 400

[[key-zones]]
pitch = 60
key-center = 60.0

[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Example Pad-000-060-c3.wav'
loop-mode = 'Off'
```

## Complete eldrum Example

```toml
# ELEKTRON DRUM SET MAPPING FORMAT
version = 0
name = "Example Drum Kit"

[[key-zones]]
pitch = 60
key-center = 60.0

[[key-zones.velocity-layers]]
velocity = 0.24705882
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = '1_Kick_ExampleKit.wav'


[[key-zones]]
pitch = 62
key-center = 62.0

[[key-zones.velocity-layers]]
velocity = 0.24705882
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = '2_Snare_ExampleKit.wav'


[[key-zones]]
pitch = 69
key-center = 69.0

[[key-zones.velocity-layers]]
velocity = 0.24705882
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = '6_ClosedHat_ExampleKit.wav'
```

**Key observations:**
- Uses double quotes for `name` field
- No `loop-mode` or loop parameters
- Sample filenames use descriptive naming without MIDI note/octave
- Default velocity is typically `0.24705882` (~MIDI 31)

---

## Appendix A: EXS24 to elmulti Parameter Mapping

### Zone Parameters

| EXS24 Parameter | elmulti Equivalent | Notes |
|-----------------|-------------------|-------|
| `rootnote` | `pitch`, `key-center` | MIDI note number |
| `startnote` / `endnote` | (implicit) | elmulti uses pitch-per-zone model |
| `minvel` / `maxvel` | `velocity` | Convert to 0.0-1.0 range |
| `loop` (flag) | `loop-mode` | 0 → `'Off'`, 1 → `'Forward'` |
| `loopstart` | `loop-start` | Sample position (integer) |
| `loopend` | `loop-end` | Sample position (integer) |
| `loopcrossfade` | `loop-crossfade` | EXS stores in ms, convert to samples: `raw × (rate/1000)` |
| `samplestart` | (not supported) | — |
| `sampleend` | (not supported) | — |
| `finetune` | (not supported) | — |
| `pan` | (not supported) | — |
| `volumeadjust` | (not supported) | — |
| `pitchtrack` | (not supported) | — |
| `oneshot` | `loop-mode = 'Off'` | — |

### Velocity Conversion

```python
# EXS velocity (0-127) to elmulti velocity (0.0-1.0)
elmulti_velocity = exs_minvel / 127.0

# Default value when single velocity layer
DEFAULT_VELOCITY = 0.49411765  # ≈ 63/127
```

### Group/Round-Robin Mapping

| EXS24 Concept | elmulti Equivalent |
|---------------|-------------------|
| Group with `sequence` | Multiple `[[sample-slots]]` |
| Group `polyphony` | (not directly supported) |
| Group `trigger` | (not supported) |
| Group `output` | (not supported) |

### Audio Format Conversion

| EXS24 (typical) | elmulti (required) |
|-----------------|-------------------|
| AIFF | WAV |
| Various sample rates | 48000 Hz (recommended) |
| Various bit depths | 16/24-bit PCM |

### Conversion Example (Python)

```python
def exs_zone_to_elmulti(zone, sample, sample_filename):
    """Convert EXS zone to elmulti key-zone structure."""
    
    result = {
        'pitch': zone.rootnote,
        'key_center': float(zone.rootnote),
        'velocity': zone.minvel / 127.0 if zone.minvel > 0 else 0.49411765,
        'sample': sample_filename,
        'loop_mode': 'Forward' if zone.loop else 'Off',
    }
    
    if zone.loop:
        result['loop_start'] = zone.loopstart
        result['loop_end'] = zone.loopend
        if zone.loopcrossfade > 0:
            # IMPORTANT: EXS stores crossfade in milliseconds
            # Convert to samples: raw_value × (sample_rate / 1000)
            crossfade_samples = zone.loopcrossfade * (sample.rate // 1000)
            result['loop_crossfade'] = crossfade_samples
    
    return result
```

---

## Appendix B: EXS24 Binary Format Reference

### Chunk Signatures

| Chunk Type | Old Signature | New Signature (0x40+) |
|------------|---------------|----------------------|
| Header | `0x00000101` | `0x40000101` |
| Zone | `0x01000101` | `0x41000101` |
| Group | `0x02000101` | `0x42000101` |
| Sample | `0x03000101` | `0x43000101` |
| Param | `0x04000101` | `0x44000101` |

### Zone Data Offsets (from chunk start)

| Offset | Size | Field |
|--------|------|-------|
| 84 | 1 | Flags (bit 0: !pitchtrack, bit 1: oneshot) |
| 85 | 1 | Root note |
| 86 | 1 | Fine tune (signed) |
| 87 | 1 | Pan (signed) |
| 88 | 1 | Volume adjust (signed) |
| 90 | 1 | Start note |
| 91 | 1 | End note |
| 93 | 1 | Min velocity |
| 94 | 1 | Max velocity |
| 96 | 4 | Sample start |
| 100 | 4 | Sample end |
| 104 | 4 | Loop start |
| 108 | 4 | Loop end |
| 112 | 4 | Loop crossfade |
| 117 | 1 | Loop flag |
| 172 | 4 | Group index (signed) |
| 176 | 4 | Sample index |

---

---

## Appendix C: SFZ Format Comparison (Tonverk Subset)

Tonverk supports a subset of the SFZ format. This appendix documents the differences and compatibility considerations.

**Source:** Tonverk Official Manual, Appendix E: SFZ Support

### Supported SFZ Headers

| Header | Support |
|--------|---------|
| `<control>` | ✓ Supported |
| `<global>` | ✓ Supported |
| `<master>` | ✓ Supported |
| `<group>` | ✓ Supported |
| `<region>` | ✓ Required |
| `<curve>` | Allowed but ignored |
| `<effect>`, `<midi>`, `<sample>` | ✗ **Error** (file will fail to load) |

### Control Opcodes

Under `<control>` header:

| Opcode | Description |
|--------|-------------|
| `default_path` | Sets the path where files are loaded relative to |
| `note_offset` | Transposes all regions by semitones |
| `octave_offset` | Transposes all regions by octaves |

Ignored control opcodes (no error): `hint_load_method`, `label_cc_*`, `set_cc_*`

### Required SFZ Opcodes

| Opcode | Description |
|--------|-------------|
| `sample` | File path (UNIX-style, relative to SFZ) |
| `key` or `pitch_keycenter` | Root note (MIDI number or IPN notation) |

**Sample file name restrictions:**
- Spaces are allowed
- `=` and balanced angle brackets (`<>`) are **not allowed**
- Comment tokens (`//`, `/*`) are **forbidden**
- `pitch_keycenter=sample` is **not supported**

### Zone Opcodes

| Opcode | elmulti Equivalent | Notes |
|--------|-------------------|-------|
| `lokey` / `hikey` | `pitch` | Processed but not used; **nearest root note is selected** |
| `lovel` / `hivel` | `velocity` | Up to 128 velocity layers supported |
| `lorand` / `hirand` | (not in elmulti) | Random sample selection within velocity layer |
| `seq_length` / `seq_position` | Multiple `[[sample-slots]]` | Ordered round-robin |

**Round-robin and random selection are mutually exclusive.**

### Playback Opcodes

| SFZ Opcode | elmulti Equivalent | Notes |
|------------|-------------------|-------|
| `offset` | `trim-start` | Samples (integer) |
| `end` | `trim-end` | Samples (integer) |
| `loop_start` | `loop-start` | Samples (integer). Can be spelled with/without underscore |
| `loop_end` | `loop-end` | Samples (integer). Can be spelled with/without underscore |
| `loop_crossfade` | `loop-crossfade` | **SFZ: seconds (float)** / **elmulti: samples (int)** |
| `loop_mode` | `loop-mode` | See table below |

**Note:** If loop points exist in WAV file's SMPL chunk and no `loop_mode` is specified, `loop_mode=loop_sustain` is implied.

### Loop Mode Mapping

| SFZ Value | elmulti Value | Additional Field | Behavior |
|-----------|---------------|------------------|----------|
| `no_loop` | `'Off'` | — | No looping |
| `one_shot` | `'Off'` | — | **Identical to no_loop on Tonverk** (per official manual) |
| `loop_sustain` | `'Forward'` | — | Loop while key held, stop on release |
| `loop_continuous` | `'Forward'` | `keep-looping-on-release = true` | Loop continues during release phase |

**Note:** The official Tonverk manual does not explicitly mention `loop_continuous` support. However, elmulti native format supports `keep-looping-on-release` for this behavior.

### Loop Mode Conversion Code

```python
# SFZ → elmulti
def sfz_loop_mode_to_elmulti(loop_mode):
    if loop_mode == 'loop_continuous':
        return {'loop-mode': 'Forward', 'keep-looping-on-release': True}
    elif loop_mode == 'loop_sustain':
        return {'loop-mode': 'Forward'}  # keep-looping-on-release omitted
    else:  # no_loop, one_shot
        return {'loop-mode': 'Off'}

# elmulti → SFZ
def elmulti_to_sfz_loop_mode(loop_mode, keep_looping_on_release=False):
    if loop_mode == 'Off':
        return 'no_loop'
    elif keep_looping_on_release:
        return 'loop_continuous'
    else:
        return 'loop_sustain'
```

### Unsupported SFZ Features on Tonverk

The following SFZ opcodes are **ignored** by Tonverk:

#### Velocity Crossfade (Not Supported)
```sfz
# These are IGNORED - Tonverk uses hard switching only
xfin_lovel=64
xfin_hivel=84
xfout_lovel=64
xfout_hivel=84
```

#### Sound Processing (Not Supported)
- `volume`, `pan`, `tune`, `pitch_keycenter`
- `ampeg_*` (envelope)
- `cutoff`, `resonance` (filter)
- All effect opcodes

### Conversion: loop_crossfade Units

```python
# SFZ (seconds) to elmulti (samples)
elmulti_crossfade = int(sfz_crossfade_seconds * sample_rate)

# Example: 0.5 seconds at 48kHz
elmulti_crossfade = int(0.5 * 48000)  # = 24000 samples

# elmulti (samples) to SFZ (seconds)
sfz_crossfade = elmulti_crossfade / sample_rate

# Example: 24000 samples at 48kHz
sfz_crossfade = 24000 / 48000  # = 0.5 seconds
```

### Feature Comparison Summary

| Feature | elmulti | SFZ (Tonverk) | SFZ (Full Spec) |
|---------|---------|---------------|-----------------|
| Velocity Layers | ✓ | ✓ | ✓ |
| Velocity Crossfade | ✗ | ✗ | ✓ |
| Loop Crossfade | ✓ (samples) | ✓ (seconds) | ✓ (seconds) |
| Loop Sustain Mode | ✓ | ✓ | ✓ |
| Loop Continuous Mode | ✓ (`keep-looping-on-release`) | ✓ | ✓ |
| Round-Robin | ✓ | ✓ | ✓ |
| Random Selection | ? | ✓ | ✓ |
| Single-File Multi-Sample | ✓ (trim-start/end) | ✗ | ✗ |
| Sound Processing | ✗ | ✗ | ✓ |
| Native Tonverk Format | ✓ | ✗ | ✗ |

### Recommended Format

| Use Case | Recommended Format |
|----------|-------------------|
| Tonverk native workflow | `.elmulti` |
| Cross-platform compatibility | `.sfz` |
| Converting from EXS24 | `.elmulti` (simpler, native) |
| Maximum feature support | `.sfz` (full spec, other players) |

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-15 | 1.0 | Initial specification based on Tonverk Factory Library analysis |
| 2024-12-15 | 1.1 | Added trim-start/trim-end, velocity behavior, SFZ comparison appendix |
| 2025-12-15 | 1.2 | Comprehensive analysis of 112 elmulti + 81 eldrum files: Added `keep-looping-on-release` field; Corrected note naming (uses `b` not `h`); Added negative octave support; Clarified elmulti vs eldrum differences; Added drum file naming convention; Made `loop-mode` optional; Added octave formula; Extended velocity reference table |
| 2025-12-15 | 1.3 | Updated SFZ loop_mode mapping: `loop_continuous` now maps to `keep-looping-on-release = true`; Added bidirectional conversion code examples |
| 2025-12-15 | 1.4 | Added SFZ vs elmulti octave notation comparison; Updated Appendix C with official Tonverk manual information; Added control opcodes, file name restrictions, WAV SMPL chunk support |
