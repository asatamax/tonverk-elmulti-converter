# GUI Implementation Plan

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| GUI Framework | **Flet** | Cross-platform, modern UI, easy D&D, simple packaging |
| ffmpeg Distribution | **static-ffmpeg** | PyPI package, auto-downloads binary, works with PyInstaller |
| Packaging | **flet pack** | Single executable for macOS/Windows |
| Python Version | **3.9+** | Wide compatibility, required by Flet |

## Project Structure

```
tonverk-elmulti-converter/
├── elmconv.py              # CLI (unchanged)
├── elmconv_gui.py          # GUI entry point
├── gui/
│   ├── __init__.py
│   ├── app.py              # Main Flet application
│   ├── components/
│   │   ├── __init__.py
│   │   ├── drop_zone.py    # Drag-and-drop component
│   │   ├── options.py      # Options panel
│   │   ├── log_view.py     # Conversion log display
│   │   └── folder_picker.py # Output folder selector
│   ├── converter.py        # Bridge to elmconv.py functions
│   ├── strings.py          # Localization strings
│   └── theme.py            # Theme configuration
├── assets/
│   └── icon.png            # App icon (1024x1024)
├── requirements.txt        # Dependencies
├── build/                  # Build outputs (gitignored)
└── docs/
    ├── GUI_SPEC.md
    └── GUI_IMPLEMENTATION_PLAN.md
```

## Dependencies

### requirements.txt

```
flet>=0.21.0
static-ffmpeg>=2.5
```

### Development Dependencies (optional)

```
pyinstaller>=6.0  # Included with flet pack
```

## Implementation Phases

### Phase 1: Project Setup

**Files to create:**
- `requirements.txt`
- `gui/__init__.py`
- `gui/strings.py`
- `gui/theme.py`

**Tasks:**
1. Create directory structure
2. Define dependency versions
3. Set up string constants for localization
4. Configure theme (light/dark detection)

### Phase 2: Core Components

**Files to create:**
- `gui/components/folder_picker.py`
- `gui/components/options.py`
- `gui/components/drop_zone.py`
- `gui/components/log_view.py`

**Component Specifications:**

#### FolderPicker
```python
class FolderPicker:
    """Output folder selection component"""
    - Text field showing selected path
    - Browse button triggering FilePicker
    - Validation (folder exists, writable)
    - Callback on selection change
```

#### OptionsPanel
```python
class OptionsPanel:
    """Conversion options component"""
    - Resample radio: 48kHz / Keep original
    - Optimize checkbox
    - Prefix text input
    - Expandable advanced section
    - Method to get current options dict
```

#### DropZone
```python
class DropZone:
    """Drag-and-drop file input component"""
    - DragTarget for file drops
    - GestureDetector for click-to-browse
    - Visual feedback on drag hover
    - File type validation (.exs, .sfz)
    - Directory handling (non-recursive)
    - Callback with list of valid file paths
```

#### LogView
```python
class LogView:
    """Conversion log display component"""
    - Scrollable log area
    - Methods: add_info(), add_success(), add_warning(), add_error()
    - Export button with FilePicker (save dialog)
    - Clear method
```

### Phase 3: Converter Bridge

**Files to create:**
- `gui/converter.py`

**Purpose:** Bridge between GUI and `elmconv.py` functions

```python
class ConverterBridge:
    """Wraps elmconv.py for GUI use"""

    def __init__(self, log_callback):
        """Initialize with callback for log messages"""

    async def convert(self, input_files, output_dir, options):
        """
        Run conversion asynchronously
        - Yields progress updates
        - Catches and reports errors
        - Returns summary statistics
        """

    def validate_output_dir(self, path) -> tuple[bool, str]:
        """Check if output directory is valid"""

    def validate_input_files(self, paths) -> list[str]:
        """Filter and validate input files, return valid paths"""
```

**Key considerations:**
- Run conversion in separate thread to avoid UI freeze
- Capture stdout/stderr for log display
- Handle `ConversionStats` from elmconv.py

### Phase 4: Main Application

**Files to create:**
- `gui/app.py`
- `elmconv_gui.py`

**Application structure:**
```python
# gui/app.py
class ElmconvApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_theme()
        self.create_components()
        self.build_layout()

    def setup_theme(self):
        """Configure light/dark theme from OS"""

    def create_components(self):
        """Initialize all UI components"""

    def build_layout(self):
        """Arrange components in page"""

    def on_files_dropped(self, files):
        """Handle file drop event"""

    def on_convert_complete(self, stats):
        """Handle conversion completion"""
```

```python
# elmconv_gui.py
import flet as ft
from gui.app import ElmconvApp

def main(page: ft.Page):
    ElmconvApp(page)

if __name__ == "__main__":
    ft.app(target=main)
```

### Phase 5: ffmpeg Integration

**Tasks:**
1. Install `static-ffmpeg` via requirements.txt
2. Add initialization code to ensure ffmpeg is available
3. Test on clean system (no pre-installed ffmpeg)

```python
# In gui/app.py or converter.py
def ensure_ffmpeg():
    """Ensure ffmpeg is available in PATH"""
    import static_ffmpeg
    static_ffmpeg.add_paths()
```

### Phase 6: Packaging & Distribution

**macOS Build:**
```bash
flet pack elmconv_gui.py \
    --name "Tonverk Elmulti Converter" \
    --icon assets/icon.png \
    --add-data "elmconv.py:." \
    --product-name "Tonverk Elmulti Converter"
```

**Windows Build:**
```bash
flet pack elmconv_gui.py ^
    --name "Tonverk Elmulti Converter" ^
    --icon assets/icon.ico ^
    --add-data "elmconv.py;." ^
    --product-name "Tonverk Elmulti Converter"
```

**Distribution files:**
- macOS: `Tonverk Elmulti Converter.app` (zip for distribution)
- Windows: `Tonverk Elmulti Converter.exe`

### Phase 7: Documentation

**Update README.md:**
- Add GUI section with screenshots
- Document "unsigned app" bypass for macOS/Windows
- Keep CLI documentation

**Create BUILDING.md:**
- Source build instructions
- Development setup
- Packaging commands

## Implementation Checklist

### Setup
- [ ] Create `requirements.txt`
- [ ] Create `gui/` directory structure
- [ ] Create `gui/strings.py` with all UI strings
- [ ] Create `gui/theme.py` with theme configuration

### Components
- [ ] Implement `FolderPicker` component
- [ ] Implement `OptionsPanel` component
- [ ] Implement `DropZone` component
- [ ] Implement `LogView` component
- [ ] Unit test each component

### Integration
- [ ] Create `ConverterBridge` class
- [ ] Implement async conversion with progress
- [ ] Handle all elmconv.py options
- [ ] Test with various input files

### Application
- [ ] Create `ElmconvApp` main class
- [ ] Implement theme detection
- [ ] Wire up all components
- [ ] Create `elmconv_gui.py` entry point
- [ ] End-to-end testing

### Distribution
- [ ] Create app icon (1024x1024 PNG)
- [ ] Build macOS app
- [ ] Test macOS app on clean system
- [ ] Build Windows exe
- [ ] Test Windows exe on clean system
- [ ] Create GitHub release

### Documentation
- [ ] Update README with GUI instructions
- [ ] Add screenshots
- [ ] Document unsigned app bypass
- [ ] Create BUILDING.md for developers

## Code Style Guidelines

### General
- Python 3.9+ syntax
- Type hints for all public methods
- Docstrings for classes and public methods
- No emoji in code or UI strings

### Flet-specific
- Use `ft.` prefix for all Flet imports
- Async for long-running operations
- `page.update()` after UI changes

### Strings
- All user-facing text in `gui/strings.py`
- Constants in UPPER_SNAKE_CASE
- Comments for context (helps translators)

## Testing Strategy

### Manual Testing Checklist
- [ ] Drop single .exs file
- [ ] Drop single .sfz file
- [ ] Drop multiple files
- [ ] Drop directory with mixed files
- [ ] Click to browse (single file)
- [ ] Click to browse (multiple files)
- [ ] All options combinations
- [ ] Export log functionality
- [ ] Light theme appearance
- [ ] Dark theme appearance
- [ ] Error handling (invalid files)
- [ ] Error handling (no output folder)
- [ ] Large file conversion (UI responsiveness)

### Platform Testing
- [ ] macOS (Apple Silicon)
- [ ] macOS (Intel)
- [ ] Windows 10
- [ ] Windows 11

## Known Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| static-ffmpeg download fails | Document manual ffmpeg install as fallback |
| Flet version incompatibility | Pin specific version in requirements.txt |
| macOS Gatekeeper blocks app | Clear documentation with screenshots |
| Windows SmartScreen warning | Clear documentation with screenshots |
| Large files freeze UI | Async conversion in separate thread |

## Timeline Estimate

| Phase | Effort |
|-------|--------|
| Phase 1: Setup | Small |
| Phase 2: Components | Medium |
| Phase 3: Converter Bridge | Medium |
| Phase 4: Main App | Medium |
| Phase 5: ffmpeg | Small |
| Phase 6: Packaging | Medium |
| Phase 7: Documentation | Small |

**Note:** This timeline is relative effort estimation only. Actual implementation time depends on developer familiarity with Flet and available time.
