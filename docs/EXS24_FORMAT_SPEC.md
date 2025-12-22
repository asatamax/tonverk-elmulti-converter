# Apple Logic Pro EXS24 Sampler Format Specification

Version: 1.0
Last Updated: 2025-12-15
Status: Reverse-engineered (based on ConvertWithMoss project analysis)

## Overview

The EXS24 format is Apple's proprietary sampler instrument format used by Logic Pro's EXS24 sampler (now called "Sampler" in newer versions). It is a binary format that defines sample mappings, zones, groups, and various playback parameters.

### References

- Primary source: [ConvertWithMoss](https://github.com/git-moss/ConvertWithMoss) by Jürgen Moßgraber
- License: LGPLv3

## File Format

### Encoding
- Binary format
- Supports both Little Endian and Big Endian (Big Endian is legacy, rarely used)
- File extension: `.exs`

### Magic Numbers / Signatures

| Chunk Type | Little Endian (Standard) | Big Endian (Legacy) |
|------------|-------------------------|---------------------|
| Header | `0x00000101` | `0x01010000` |
| Zone | `0x01000101` | `0x01010001` |
| Group | `0x02000101` | `0x01010002` |
| Sample | `0x03000101` | `0x01010003` |
| Parameters | `0x04000101` | `0x01010004` |

**New format signatures** (0x40+ prefix):

| Chunk Type | New Signature |
|------------|---------------|
| Header | `0x40000101` |
| Zone | `0x41000101` |
| Group | `0x42000101` |
| Sample | `0x43000101` |
| Parameters | `0x44000101` |

### File Structure

```
[Header Block]
[Zone Block 1]
[Zone Block 2]
...
[Group Block 1]
[Group Block 2]
...
[Sample Block 1]
[Sample Block 2]
...
[Parameters Block] (optional)
```

### Block Structure

Each block follows this structure:

| Offset | Size | Description |
|--------|------|-------------|
| 0 | 4 | Signature (chunk type) |
| 4 | 4 | Data size (excluding 84-byte header) |
| 8 | 4 | Object ID |
| 12 | 8 | Reserved/Unknown |
| 20 | 64 | Object name (null-terminated UTF-8) |
| 84 | varies | Block-specific data |

---

## Zone Structure

A Zone defines how a sample is mapped to the keyboard with pitch, velocity, and loop settings.

### Zone Data Layout (from offset 84)

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 1 | Flags | zoneOptions | See Zone Options Flags |
| 1 | 1 | uint8 | key | Root note (MIDI 0-127) |
| 2 | 1 | int8 | fineTuning | Fine tune in cents (-128 to +127) |
| 3 | 1 | int8 | pan | Pan position (-64 to +63) |
| 4 | 1 | int8 | volumeAdjust | Volume adjustment in dB |
| 5 | 1 | uint8 | volumeScale | Volume scaling |
| 6 | 1 | uint8 | keyLow | Lowest key in range |
| 7 | 1 | uint8 | keyHigh | Highest key in range |
| 8 | 1 | — | (reserved) | |
| 9 | 1 | uint8 | velocityLow | Minimum velocity |
| 10 | 1 | uint8 | velocityHigh | Maximum velocity |
| 11 | 1 | — | (reserved) | |
| 12 | 4 | uint32 | sampleStart | Sample start position |
| 16 | 4 | uint32 | sampleEnd | Sample end position |
| 20 | 4 | uint32 | loopStart | Loop start position |
| 24 | 4 | uint32 | loopEnd | Loop end position |
| 28 | 4 | uint32 | loopCrossfade | Loop crossfade in milliseconds |
| 32 | 1 | uint8 | loopTune | Loop tuning |
| 33 | 1 | Flags | loopOptions | See Loop Options Flags |
| 34 | 1 | uint8 | loopDirection | Loop direction (see below) |
| 35-76 | 42 | — | (reserved) | |
| 77 | 1 | uint8 | flexOptions | Flex time options |
| 78 | 1 | uint8 | flexSpeed | Flex speed |
| 79 | 1 | uint8 | tailTune | Tail tuning |
| 80 | 1 | int8 | coarseTuning | Coarse tune in semitones |
| 81 | 1 | — | (reserved) | |
| 82 | 1 | uint8 | output | Output assignment (-1 = default) |
| 83-87 | 5 | — | (reserved) | |
| 88 | 4 | int32 | groupIndex | Group reference (-1 = none) |
| 92 | 4 | uint32 | sampleIndex | Sample reference |

### Zone Options Flags (offset 0)

| Bit | Name | Description |
|-----|------|-------------|
| 0 | oneshot | One-shot mode (ignore note-off) |
| 1 | !pitch | Pitch tracking OFF (inverted: 0 = tracking ON) |
| 2 | reverse | Reverse playback |
| 3 | velocityRangeOn | Velocity range is active |
| 6 | outputAssigned | Output assignment is valid |

### Loop Options Flags (offset 33)

| Bit | Name | Description |
|-----|------|-------------|
| 0 | loopOn | Loop is enabled |
| 1 | loopEqualPower | Equal power crossfade |
| 2 | loopPlayToEndOnRelease | Play to sample end on key release (NOT keep looping) |

**Important:** `loopPlayToEndOnRelease` is the **inverse** of elmulti's `keep-looping-on-release`:
- EXS24: `loopPlayToEndOnRelease = true` → Stop looping on release, play to end
- EXS24: `loopPlayToEndOnRelease = false` → Keep looping through release phase

### Loop Direction Values

| Value | Mode |
|-------|------|
| 0 | Forward |
| 1 | Backward |
| 2 | Ping-Pong (Alternate) |

---

## Group Structure

A Group defines shared properties for multiple zones, including round-robin and trigger settings.

### Group Data Layout (from offset 84)

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 1 | uint8 | volume | Group volume |
| 1 | 1 | uint8 | pan | Group pan |
| 2 | 1 | uint8 | polyphony | Max polyphony (0 = unlimited) |
| 3 | 1 | Flags | options | See Group Options Flags |
| 4 | 1 | uint8 | exclusive | Exclusive group ID |
| 5 | 1 | uint8 | minVelocity | Minimum velocity filter |
| 6 | 1 | uint8 | maxVelocity | Maximum velocity filter |
| 7 | 1 | uint8 | sampleSelectRandomOffset | Random sample selection offset |
| 8-15 | 8 | — | (reserved) | |
| 16 | 2 | uint16 | releaseTriggerTime | Release trigger time |
| 18-31 | 14 | — | (reserved) | |
| 32 | 1 | int8 | velocityRangExFade | Velocity crossfade amount |
| 33 | 1 | uint8 | velocityRangExFadeType | Velocity crossfade type |
| 34 | 1 | uint8 | keyrangExFadeType | Key range crossfade type |
| 35 | 1 | int8 | keyrangExFade | Key range crossfade amount |
| 36-37 | 2 | — | (reserved) | |
| 38 | 1 | uint8 | enableByTempoLow | Tempo range low (default: 80) |
| 39 | 1 | uint8 | enableByTempoHigh | Tempo range high (default: 140) |
| 40 | 1 | — | (reserved) | |
| 41 | 1 | uint8 | cutoffOffset | Filter cutoff offset |
| 42 | 1 | — | (reserved) | |
| 43 | 1 | uint8 | resoOffset | Filter resonance offset |
| 44-55 | 12 | — | (reserved) | |
| 56 | 4 | uint32 | env1AttackOffset | Envelope 1 attack offset |
| 60 | 4 | uint32 | env1DecayOffset | Envelope 1 decay offset |
| 64 | 4 | uint32 | env1SustainOffset | Envelope 1 sustain offset |
| 68 | 4 | uint32 | env1ReleaseOffset | Envelope 1 release offset |
| 72 | 1 | — | (reserved) | |
| 73 | 1 | bool | releaseTrigger | Release trigger enabled |
| 74 | 1 | uint8 | output | Output assignment |
| 75 | 1 | uint8 | enableByNoteValue | Note value for enable |
| 76-79 | 4 | — | (reserved) | |
| 80 | 4 | int32 | roundRobinGroupPos | Round-robin position (-1 = none) |
| 84 | 1 | uint8 | enableByType | Enable condition type (see below) |
| 85 | 1 | uint8 | enableByControlValue | CC number for control enable |
| 86 | 1 | uint8 | enableByControlLow | CC range low |
| 87 | 1 | uint8 | enableByControlHigh | CC range high |
| 88 | 1 | uint8 | startNote | Start note for note enable |
| 89 | 1 | uint8 | endNote | End note for note enable |
| 90 | 1 | uint8 | enableByMidiChannel | MIDI channel filter |
| 91 | 1 | uint8 | enableByArticulationValue | Articulation ID |

### Group Options Flags (offset 3)

| Bit | Value | Name | Description |
|-----|-------|------|-------------|
| 4 | 16 | mute | Group is muted |
| 6 | 64 | releaseTriggerDecay | Release trigger with decay |
| 7 | 128 | fixedSampleSelect | Fixed sample selection |

### Enable By Type Values

| Value | Type | Description |
|-------|------|-------------|
| 0 | None | Always enabled |
| 1 | Note | Enable by specific note |
| 2 | Round-Robin | Round-robin selection |
| 3 | Control | Enable by CC value |
| 4 | Bend | Enable by pitch bend |
| 5 | Channel | Enable by MIDI channel |
| 6 | Articulation | Enable by articulation ID |
| 7 | Tempo | Enable by tempo range |

---

## Sample Structure

A Sample defines the audio file reference and its properties.

### Sample Data Layout (from offset 84)

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 4 | uint32 | waveDataStart | Offset to wave data in embedded samples |
| 4 | 4 | uint32 | length | Sample length in frames |
| 8 | 4 | uint32 | sampleRate | Sample rate in Hz |
| 12 | 4 | uint32 | bitDepth | Bit depth (16, 24, 32) |
| 16 | 4 | uint32 | channels | Number of channels |
| 20 | 4 | uint32 | channels2 | Secondary channel count |
| 24-27 | 4 | — | (reserved) | |
| 28 | 4 | ASCII | type | File type identifier (e.g., "WAVE", "AIFF") |
| 32 | 4 | uint32 | size | File size |
| 36 | 4 | uint32 | isCompressed | Compression flag (0 = uncompressed) |
| 40-79 | 40 | — | (reserved) | |
| 80 | 256 | string | filePath | Full file path (null-terminated) |
| 336 | 256 | string | fileName | File name only (null-terminated) |

---

## Format Mapping Tables

### EXS24 → elmulti Mapping

| EXS24 Field | elmulti Field | Conversion Notes |
|-------------|---------------|------------------|
| `key` | `pitch`, `key-center` | Direct mapping |
| `keyLow`, `keyHigh` | (implicit) | elmulti uses single pitch per zone |
| `velocityLow` | `velocity` | Convert: `velocityLow / 127.0` |
| `velocityHigh` | — | Not directly supported |
| `loopOn` | `loop-mode` | `true` → `'Forward'`, `false` → `'Off'` |
| `loopStart` | `loop-start` | Direct mapping |
| `loopEnd` | `loop-end` | Direct mapping |
| `loopCrossfade` | `loop-crossfade` | Convert: ms → samples (`raw × (rate/1000)`) |
| `loopPlayToEndOnRelease` | `keep-looping-on-release` | **Inverted**: `false` → `true` |
| `loopDirection` | — | Only Forward supported in elmulti |
| `sampleStart` | `trim-start` | Direct mapping |
| `sampleEnd` | `trim-end` | Direct mapping |
| `oneshot` | `loop-mode = 'Off'` | One-shot = no loop |
| `reverse` | — | Not supported in elmulti |
| `fineTuning` | — | Not supported in elmulti |
| `pan` | — | Not supported in elmulti |
| `volumeAdjust` | — | Not supported in elmulti |
| `coarseTuning` | — | Not supported in elmulti |
| Group `roundRobinGroupPos` | Multiple `[[sample-slots]]` | See round-robin conversion |

### EXS24 → SFZ Mapping

| EXS24 Field | SFZ Opcode | Conversion Notes |
|-------------|------------|------------------|
| `key` | `pitch_keycenter` | Direct mapping |
| `keyLow` | `lokey` | Direct mapping |
| `keyHigh` | `hikey` | Direct mapping |
| `velocityLow` | `lovel` | Direct mapping (0-127) |
| `velocityHigh` | `hivel` | Direct mapping (0-127) |
| `loopOn` | `loop_mode` | `true` → `loop_sustain` |
| `loopStart` | `loop_start` | Direct mapping |
| `loopEnd` | `loop_end` | Direct mapping |
| `loopCrossfade` | `loop_crossfade` | Convert: ms → seconds (`raw / 1000`) |
| `loopPlayToEndOnRelease` | `loop_mode` | `false` → `loop_continuous` |
| `loopDirection` | — | SFZ v1 doesn't support |
| `sampleStart` | `offset` | Direct mapping |
| `sampleEnd` | `end` | Direct mapping |
| `oneshot` | `loop_mode=one_shot` | Direct mapping |
| `reverse` | `direction=reverse` | SFZ v2 opcode |
| Group `roundRobinGroupPos` | `seq_position` | With `seq_length` |

---

## Round-Robin Conversion

### EXS24 Round-Robin Structure

In EXS24, round-robin is implemented via Groups:
1. Multiple Groups with `enableByType = 2` (Round-Robin)
2. Each Group has a `roundRobinGroupPos` value (0, 1, 2, ...)
3. Zones reference their Group via `groupIndex`

### Conversion to elmulti

```toml
# Multiple sample-slots under one velocity-layer = round-robin
[[key-zones.velocity-layers.sample-slots]]
sample = 'Sample_RR1.wav'
loop-mode = 'Off'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Sample_RR2.wav'
loop-mode = 'Off'

[[key-zones.velocity-layers.sample-slots]]
sample = 'Sample_RR3.wav'
loop-mode = 'Off'
```

### Conversion to SFZ

```sfz
<group>
seq_length=3

<region> seq_position=1 sample=Sample_RR1.wav
<region> seq_position=2 sample=Sample_RR2.wav
<region> seq_position=3 sample=Sample_RR3.wav
```

---

## Information Loss Matrix

When converting between formats, some information is lost:

| Feature | EXS24 | elmulti | SFZ | Loss Direction |
|---------|-------|---------|-----|----------------|
| Pitch tracking | ✓ | ✗ | ✓ | EXS→elmulti |
| Fine tuning | ✓ | ✗ | ✓ | EXS→elmulti |
| Pan | ✓ | ✗ | ✓ | EXS→elmulti |
| Volume adjust | ✓ | ✗ | ✓ | EXS→elmulti |
| Reverse | ✓ | ✗ | ✓ | EXS→elmulti |
| Loop direction | ✓ | ✗ | ✗ | EXS→both |
| Key range | ✓ | ✗ | ✓ | EXS→elmulti |
| Velocity crossfade | ✓ | ✗ | ✓ | EXS→elmulti |
| Filter/Envelope | ✓ | ✗ | ✓ | EXS→elmulti |
| Exclusive groups | ✓ | ✗ | ✓ | EXS→elmulti |
| Release trigger | ✓ | ✗ | ✓ | EXS→elmulti |
| Random selection | ✗ | ? | ✓ | SFZ→EXS |
| Single-file multi | ✗ | ✓ | ✗ | elmulti→both |

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-15 | 1.0 | Initial specification based on ConvertWithMoss analysis |
