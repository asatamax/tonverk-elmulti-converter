# Tonverk Elmulti Converter GUI Specification

## Overview

A graphical user interface for `elmconv.py` that enables non-technical users to convert EXS24/SFZ instruments to Elektron Tonverk's `.elmulti` format through a simple drag-and-drop workflow.

## Goals

1. **Accessibility**: Users unfamiliar with CLI or Homebrew can use the converter
2. **Simplicity**: Minimal, modern interface with essential options only
3. **Cross-platform**: macOS (primary), Windows (supported)
4. **Developer-friendly**: Source code remains open for CLI users and custom builds

## Target Users

| User Type | Needs |
|-----------|-------|
| **Primary**: Musicians/Producers | Pre-built app, drag-and-drop, no terminal |
| **Secondary**: Technical users | Source code access, CLI, custom builds |

---

## Design Principles

### Visual Design

- **No emoji**: Use system symbols (SF Symbols on macOS, Segoe MDL2 on Windows)
- **Theme**: Follow OS light/dark mode automatically
- **Style**: Clean, minimal, modern aesthetic
- **Typography**: System fonts for native feel

### Interaction Design

- **Input**: Drag-and-drop zone (also clickable for file browser)
- **Output**: Explicit folder selection (required before conversion)
- **Feedback**: Real-time log with optional export
- **Options**: Essential settings visible, advanced options collapsed

---

## UI Layout

```
+-------------------------------------------------------+
|  Tonverk Elmulti Converter                            |
+-------------------------------------------------------+
|                                                       |
|  OUTPUT FOLDER                                        |
|  +-----------------------------------------------+    |
|  | [folder icon] /path/to/output        [Browse] |    |
|  +-----------------------------------------------+    |
|                                                       |
|  OPTIONS                                              |
|  +-----------------------------------------------+    |
|  | Resample:  (*) 48 kHz   ( ) Keep original     |    |
|  | [x] Optimize loop points                      |    |
|  | Prefix: [____________________________]        |    |
|  |                                               |    |
|  | [>] Advanced options                          |    |
|  +-----------------------------------------------+    |
|                                                       |
|  +-----------------------------------------------+    |
|  |                                               |    |
|  |    [folder icon] Drop EXS / SFZ files here    |    |
|  |              or click to browse               |    |
|  |                                               |    |
|  +-----------------------------------------------+    |
|                                                       |
|  CONVERSION LOG                          [Export]     |
|  +-----------------------------------------------+    |
|  | Ready to convert...                           |    |
|  |                                               |    |
|  +-----------------------------------------------+    |
|                                                       |
+-------------------------------------------------------+
```

### Components

#### 1. Output Folder Section
- Folder path display with native folder icon
- "Browse" button opens system folder picker
- **Required**: Must be set before conversion starts

#### 2. Options Section

**Basic Options (always visible)**:
| Option | Control | Default | Description |
|--------|---------|---------|-------------|
| Resample | Radio buttons | 48 kHz | Target sample rate |
| Optimize loop | Checkbox | Enabled | Optimize loop points for seamless playback |
| Prefix | Text input | Empty | Prefix for output instrument names |

**Advanced Options (collapsed by default)**:
| Option | Control | Default | CLI equivalent |
|--------|---------|---------|----------------|
| Normalize | Checkbox + dB input | Disabled | `-N, --normalize` |
| Loop search range | Number input | 5 | `--loop-search-range` |
| Single-cycle threshold | Number input | 512 | `--single-cycle-threshold` |
| Skip loop embedding | Checkbox | Disabled | `--no-embed-loop` |

#### 3. Drop Zone
- Large, clearly defined area
- Accepts: `.exs`, `.sfz` files, and directories (non-recursive)
- Visual feedback on drag hover
- Click to open file browser (multi-select enabled)
- Directory drops process all `.exs`/`.sfz` files in that directory only (not recursive)

#### 4. Conversion Log
- Real-time output during conversion
- Success: checkmark icon + summary
- Warning: warning icon + message
- Error: error icon + message
- "Export" button saves log to `.txt` file

---

## Behavior Specifications

### Conversion Flow

```
1. User sets output folder (required)
2. User configures options (optional)
3. User drops files or clicks to browse
4. Validation:
   - Output folder exists and is writable
   - Input files are valid (.exs or .sfz)
5. Conversion starts immediately
6. Progress shown in log area
7. Completion summary displayed
```

### File Handling

| Input | Behavior |
|-------|----------|
| Single file | Convert immediately |
| Multiple files | Convert sequentially, show progress |
| Directory | Find `.exs`/`.sfz` in top level only (non-recursive) |
| Invalid file | Show error in log, continue with others |

### Error Handling

- Missing output folder: Highlight field, show message
- Invalid input files: Log error, skip file, continue
- ffmpeg not found: Show setup instructions
- Conversion failure: Log detailed error, continue with remaining files

---

## Localization Strategy

### Phase 1 (Initial Release)
- English only
- All user-facing strings in constants/resource file

### Phase 2 (Future)
- String extraction to JSON/YAML resource files
- Language detection from OS settings
- Initial targets: Japanese, German (large Elektron user bases)

### Implementation

```python
# Centralized strings for future localization
class Strings:
    APP_TITLE = "Tonverk Elmulti Converter"
    DROP_ZONE_TEXT = "Drop EXS / SFZ files here"
    DROP_ZONE_SUBTEXT = "or click to browse"
    OUTPUT_FOLDER = "Output Folder"
    # ...
```

---

## Platform Considerations

### macOS (Primary)

- Native appearance via Flet's macOS styling
- SF Symbols for icons where available
- `.app` bundle distribution
- Unsigned app warning: Document "right-click > Open" workaround
- Gatekeeper bypass instructions in README

### Windows (Supported)

- Native appearance via Flet's Windows styling
- Segoe MDL2 icons as fallback
- `.exe` distribution
- SmartScreen warning: Document bypass procedure

### Source Build (Both Platforms)

For technical users who prefer building from source:

```bash
# Clone repository
git clone https://github.com/user/tonverk-elmulti-converter.git
cd tonverk-elmulti-converter

# Install dependencies
pip install -r requirements.txt

# Run GUI
python elmconv_gui.py

# Or use CLI directly
python elmconv.py input.exs output/
```

Benefits:
- No code signing required
- Latest features immediately
- Full CLI access
- Custom modifications possible

---

## Future Considerations

### Reverse Conversion (elmulti -> EXS/SFZ)

The UI is designed to accommodate future reverse conversion:

```
+---------------------------+---------------------------+
| EXS/SFZ -> Elmulti        | Elmulti -> EXS/SFZ        |
| [Active Tab]              | [Coming Soon - Disabled]  |
+---------------------------+---------------------------+
```

Or: Auto-detect input format and convert to the opposite format.

### Additional Features (Post-MVP)

- Batch processing queue with pause/cancel
- Preset save/load for options
- Recent folders history
- Conversion statistics dashboard

---

## Acceptance Criteria

### MVP Requirements

- [ ] Output folder selection with browse button
- [ ] Basic options (resample, optimize, prefix)
- [ ] Advanced options (collapsed)
- [ ] Drag-and-drop zone for files and directories
- [ ] Click-to-browse functionality
- [ ] Real-time conversion log
- [ ] Log export functionality
- [ ] Light/dark theme support
- [ ] macOS build and distribution
- [ ] Windows build and distribution
- [ ] Source build instructions

### Quality Requirements

- [ ] Responsive UI during conversion (no freezing)
- [ ] Clear error messages for common issues
- [ ] Consistent visual design across platforms
- [ ] All strings centralized for future localization
