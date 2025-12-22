# elmconv Format Mapping Reference

Version: 2.0
Last Updated: 2025-12-15
Status: Complete implementation reference for elmconv.py

## Overview

This document provides the definitive mapping between EXS24, SFZ, and elmulti formats as implemented in `elmconv.py`. All mappings have been verified and tested.

---

## Quick Reference

| Property | EXS24 | SFZ | elmulti |
|----------|-------|-----|---------|
| File Type | Binary | Text | Text (TOML-like) |
| Extension | `.exs` | `.sfz` | `.elmulti` |
| Native to | Logic Pro | Universal | Tonverk |

---

## Complete Mapping Matrix

### elmconv Implementation Status: 100% Complete

| elmulti Output | zone_data Key | EXS24 Source | SFZ Source | Unit Conversion | Status |
|----------------|---------------|--------------|------------|-----------------|--------|
| **Header** |
| `version` | (fixed: 0) | — | — | — | ✓ |
| `name` | instrument_name | filename | filename | — | ✓ |
| **[[key-zones]]** |
| `pitch` | pitch | `zone.rootnote` | `key` / `pitch_keycenter` | — | ✓ |
| `key-center` | key_center | `zone.rootnote` | `pitch_keycenter - transpose` | See §2.5 | ✓ |
| **[[key-zones.velocity-layers]]** |
| `velocity` | minvel / 127.0 | `zone.minvel` | `lovel` | 0-127 → 0.0-1.0 | ✓ |
| `strategy` | (fixed: 'Forward') | — | — | — | ✓ |
| **[[key-zones.velocity-layers.sample-slots]]** |
| `sample` | new_filename | `sample.name` + `sample.file_path` | `sample` + `default_path` | — | ✓ |
| `trim-start` | trim_start | `zone.samplestart` | `offset` | — | ✓ |
| `trim-end` | trim_end | `zone.sampleend` | `end` | — | ✓ |
| `loop-mode` | loop | `zone.loop` | `loop_mode` | bool → string | ✓ |
| `loop-start` | loop_start | `zone.loopstart` | `loop_start` | — | ✓ |
| `loop-end` | loop_end | `zone.loopend` | `loop_end` | — | ✓ |
| `loop-crossfade` | loop_crossfade_ms | `zone.loopcrossfade` | `loop_crossfade` | EXS:ms, SFZ:sec → samples | ✓ |
| `keep-looping-on-release` | keep_looping_on_release | `!zone.loop_play_to_end_on_release` | `loop_mode=loop_continuous` | inverted (EXS) | ✓ |
| **Round-Robin** |
| (multiple sample-slots) | rr_position | `group.round_robin_position` | `seq_position` | — | ✓ |

---

## Detailed Field Mappings

### 1. Sample Path Resolution

#### EXS24
```
Sample chunk contains:
- file_path (offset 164, 256 bytes): Directory path
- file_name (offset 420, 256 bytes): Filename

Full path = file_path + "/" + file_name
If file_path is relative, resolve from EXS directory.
```

#### SFZ
```
Region contains:
- sample: Relative path from SFZ file
- default_path (in <control>): Optional prefix

Full path = sfz_dir + "/" + default_path + "/" + sample
```

### 2. Transpose / Key-Center (SFZ Only)

The SFZ `transpose` opcode shifts the playback pitch of a sample. This is converted to `key-center` in elmulti.

#### Understanding the Conversion

**SFZ behavior:**
- `pitch_keycenter=60`: The sample plays at original pitch when MIDI note 60 is pressed
- `transpose=-24`: Shift playback pitch down by 24 semitones (2 octaves)
- Result: Pressing MIDI 60 produces a pitch 2 octaves lower (sample plays at 1/4 speed)

**elmulti behavior:**
- `key-center`: The MIDI note at which the sample plays at original pitch
- To get the same pitch shift, we adjust key-center

**Formula:**
```python
key_center = pitch_keycenter - transpose
```

**Example:**
```
SFZ:
  pitch_keycenter=60
  transpose=-24

Calculation:
  key_center = 60 - (-24) = 84

elmulti output:
  pitch = 60       # Triggered by MIDI note 60
  key-center = 84  # Sample's "root" is treated as note 84

Result:
  When MIDI 60 is pressed, sample is pitched down by (84-60)=24 semitones
  This matches the SFZ transpose=-24 behavior
```

**Why this works (counterintuitive!):**
- Setting `key-center` higher than `pitch` causes the sample to play *slower* (lower pitch)
- This is because elmulti interprets "the sample is recorded at note 84, but we're playing note 60, so pitch it down"
- The formula `key_center = pitch_keycenter - transpose` correctly inverts the transpose direction

**EXS24:** Does not have a transpose equivalent; `key_center = pitch` (rootnote).

---

### 3. Trim Points (Sample Start/End)

All values are **absolute sample positions** within the WAV file.

| Format | Start Field | End Field | Unit |
|--------|-------------|-----------|------|
| EXS24 | `zone.samplestart` | `zone.sampleend` | samples |
| SFZ | `offset` | `end` | samples |
| elmulti | `trim-start` | `trim-end` | samples |

**Behavior:** Only output to elmulti if value > 0.

### 3. Loop Settings

#### Loop Mode Mapping

| EXS24 | SFZ | elmulti | Behavior |
|-------|-----|---------|----------|
| `loop=false` | `loop_mode=no_loop` | `loop-mode='Off'` | No looping |
| `loop=true, loopPlayToEndOnRelease=true` | `loop_mode=loop_sustain` | `loop-mode='Forward'` | Loop while held |
| `loop=true, loopPlayToEndOnRelease=false` | `loop_mode=loop_continuous` | `loop-mode='Forward'` + `keep-looping-on-release=true` | Loop through release |
| `oneshot=true` | `loop_mode=one_shot` | `loop-mode='Off'` | One-shot playback |

**Important:** EXS24's `loopPlayToEndOnRelease` is **inverted** from elmulti's `keep-looping-on-release`:
- EXS24: `true` = stop looping on release
- elmulti: `true` = continue looping on release

#### Loop Crossfade Unit Conversion

| Format | Unit | Conversion to elmulti |
|--------|------|----------------------|
| EXS24 | milliseconds | `samples = ms * (sample_rate / 1000)` |
| SFZ | seconds | `samples = seconds * sample_rate` |
| elmulti | samples | (native) |

### 4. Velocity Mapping

| Format | Range | Default | Conversion |
|--------|-------|---------|------------|
| EXS24 | 0-127 (integer) | — | `velocity = minvel / 127.0` |
| SFZ | 0-127 (integer) | 0-127 | `velocity = lovel / 127.0` |
| elmulti | 0.0-1.0 (float) | 0.49411765 (~63/127) | (native) |

**Note:** When `minvel=0`, elmconv uses default velocity `0.49411765`.

### 5. Round-Robin

| Format | Group Field | Position Field | Conversion |
|--------|-------------|----------------|------------|
| EXS24 | `group.enable_by_type=2` | `group.round_robin_position` | position as-is |
| SFZ | — | `seq_position` | `rr_position = seq_position - 1` |
| elmulti | — | (multiple sample-slots) | order in array |

---

## Intermediate Data Structure (zone_data)

```python
zone_data = {
    # Required
    "pitch": int,              # MIDI note number (0-127)
    "key_center": int,         # Key center for pitch calculation (= pitch - transpose)
    "minvel": int,             # Minimum velocity (0-127)
    "maxvel": int,             # Maximum velocity (0-127)
    "source_path": str,        # Full path to source audio file
    "sample_name": str,        # Original sample filename

    # Trim
    "trim_start": int,         # Sample start position (0 = beginning)
    "trim_end": int,           # Sample end position (0 = end of file)

    # Loop
    "loop": bool,              # Loop enabled
    "loop_start": int,         # Loop start (samples)
    "loop_end": int,           # Loop end (samples)
    "loop_crossfade_ms": int,  # Crossfade (milliseconds, converted later)
    "keep_looping_on_release": bool,  # Continue loop after release

    # Round-robin
    "rr_position": int,        # Round-robin position (-1 = none)

    # Audio info
    "original_rate": int,      # Original sample rate (Hz)

    # Assigned during processing
    "vel_layer": int,          # Velocity layer index (assigned by parser)
    "new_filename": str,       # Output WAV filename (assigned by writer)
    "resample_ratio": float,   # Resampling ratio (assigned by writer)
    "output_rate": int,        # Output sample rate (assigned by writer)
}
```

---

## Unit Conversion Formulas

### Velocity
```python
# EXS24/SFZ (0-127) → elmulti (0.0-1.0)
elmulti_velocity = midi_velocity / 127.0

# elmulti (0.0-1.0) → SFZ (0-127)
sfz_lovel = int(elmulti_velocity * 127)
```

### Loop Crossfade
```python
# EXS24 (ms) → elmulti (samples)
crossfade_samples = crossfade_ms * (sample_rate // 1000)

# SFZ (seconds) → elmulti (samples)
crossfade_samples = int(crossfade_seconds * sample_rate)

# elmulti (samples) → SFZ (seconds)
crossfade_seconds = crossfade_samples / sample_rate
```

### Note Names (for filenames)
```python
# MIDI note → elmulti note name
NOTE_NAMES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]
octave = (midi_note // 12) - 2
note = NOTE_NAMES[midi_note % 12]
name = f"{note}{octave}"  # e.g., "c3" for MIDI 60

# MIDI note → SFZ IPN notation
octave = (midi_note // 12) - 1
name = f"{NOTE_NAMES[midi_note % 12].upper()}{octave}"  # e.g., "C4" for MIDI 60
```

---

## Information Loss Matrix

### EXS24 → elmulti (Not Converted)

| EXS24 Field | Reason |
|-------------|--------|
| `finetune` | elmulti doesn't support |
| `pan` | elmulti doesn't support |
| `volumeadjust` | elmulti doesn't support |
| `pitchtrack` | elmulti doesn't support |
| `coarseTuning` | elmulti doesn't support |
| `reverse` | elmulti doesn't support |
| `loopDirection` (ping-pong) | elmulti only supports forward |
| `keyLow` / `keyHigh` | elmulti uses pitch-per-zone model |
| Velocity crossfade | elmulti uses hard switching |
| Filter/Envelope offsets | elmulti doesn't support |
| Exclusive groups | elmulti doesn't support |
| Release trigger | elmulti doesn't support |

### SFZ → elmulti (Not Converted)

| SFZ Opcode | Reason |
|------------|--------|
| `tune` | elmulti doesn't support fine tuning |
| `pan` / `volume` | elmulti doesn't support |
| `lorand` / `hirand` | Random selection not implemented |
| `xfin_*` / `xfout_*` | Velocity crossfade not supported |
| `ampeg_*` | Envelope not supported |
| `cutoff` / `resonance` | Filter not supported |
| All effect opcodes | Effects not supported |
| `direction=reverse` | elmulti doesn't support |
| `note_offset` / `octave_offset` | Not implemented |

### SFZ → elmulti (Converted)

| SFZ Opcode | elmulti Field | Notes |
|------------|---------------|-------|
| `transpose` | `key-center` | See §2 for conversion formula |

---

## Conversion Examples

### EXS24 Zone → elmulti

```python
# Input: EXS24 zone
zone.rootnote = 60
zone.minvel = 64
zone.samplestart = 100
zone.sampleend = 50000
zone.loop = True
zone.loopstart = 10000
zone.loopend = 45000
zone.loopcrossfade = 50  # ms
zone.loop_play_to_end_on_release = False  # = keep looping

# Output: elmulti
[[key-zones]]
pitch = 60
key-center = 60.0

[[key-zones.velocity-layers]]
velocity = 0.503937  # 64/127
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument-000-060-c3.wav'
trim-start = 100
trim-end = 50000
loop-mode = 'Forward'
loop-start = 10000
loop-end = 45000
loop-crossfade = 2400  # 50ms * 48000/1000
keep-looping-on-release = true
```

### SFZ Region → elmulti

```python
# Input: SFZ region
<region>
sample=samples/piano_c4.wav
pitch_keycenter=60
lovel=0
hivel=127
offset=500
end=100000
loop_mode=loop_continuous
loop_start=5000
loop_end=90000
loop_crossfade=0.5  # seconds

# Output: elmulti
[[key-zones]]
pitch = 60
key-center = 60.0

[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument-000-060-c3.wav'
trim-start = 500
trim-end = 100000
loop-mode = 'Forward'
loop-start = 5000
loop-end = 90000
loop-crossfade = 24000  # 0.5 * 48000
keep-looping-on-release = true
```

### SFZ Region with Transpose → elmulti

```python
# Input: SFZ region with transpose (common in soundfonts)
<region>
sample=samples/horn.wav
pitch_keycenter=60
transpose=-24  # Play 2 octaves lower (sample is high-pitched)
loop_mode=loop_continuous
loop_start=4752
loop_end=4815

# Conversion:
# key_center = pitch_keycenter - transpose = 60 - (-24) = 84

# Output: elmulti
[[key-zones]]
pitch = 60
key-center = 84.0  # Higher key-center = sample plays slower/lower

[[key-zones.velocity-layers]]
velocity = 0.49411765
strategy = 'Forward'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Instrument-000-060-c3.wav'
loop-mode = 'Forward'
loop-start = 4752
loop-end = 4815
keep-looping-on-release = true
```

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-15 | 1.0 | Initial mapping reference |
| 2025-12-15 | 2.0 | Complete rewrite: Added complete implementation matrix; Added trim-start/trim-end mapping; Added zone_data intermediate structure; Verified all mappings against elmconv.py implementation; Added unit conversion formulas; Updated information loss matrix |
| 2025-12-16 | 2.1 | Added SFZ transpose support: key_center = pitch_keycenter - transpose; Added §2 (Transpose/Key-Center) with detailed explanation; Added conversion example with transpose; Updated zone_data structure |
