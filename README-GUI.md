# Tonverk Elmulti Converter - GUI

A graphical interface for converting EXS24 and SFZ instruments to Tonverk's `.elmulti` format.

## Download

Download the latest release for your platform:

| Platform | Download |
|----------|----------|
| macOS (Apple Silicon) | [elmconv-gui-mac-arm64.zip](https://github.com/asatamax/tonverk-elmulti-converter/releases/latest/download/elmconv-gui-mac-arm64.zip) |
| macOS (Intel) | [elmconv-gui-mac-x64.zip](https://github.com/asatamax/tonverk-elmulti-converter/releases/latest/download/elmconv-gui-mac-x64.zip) |
| Windows | [elmconv-gui-windows.zip](https://github.com/asatamax/tonverk-elmulti-converter/releases/latest/download/elmconv-gui-windows.zip) |

## Requirements

### ffmpeg

This application requires `ffmpeg` with soxr resampler support for high-quality audio conversion.

#### macOS

```bash
brew install ffmpeg
```

#### Windows

1. Download from https://ffmpeg.org/download.html
   - Choose "Windows builds" → "full" build (not "essentials")
2. Extract the archive
3. Add the `bin/` folder to your system PATH

#### Linux

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

## macOS Security Warning

Since the app is not signed with an Apple Developer certificate, macOS will show a security warning.

### Option 1: Allow in System Settings

1. Try to open the app (it will be blocked)
2. Go to **System Settings** → **Privacy & Security**
3. Scroll down and click **"Open Anyway"** next to the app name

### Option 2: Remove quarantine attribute

```bash
xattr -cr /path/to/Tonverk\ Elmulti\ Converter.app
```

## Build from Source

For advanced users who prefer to build from source:

```bash
# Clone the repository
git clone https://github.com/asatamax/tonverk-elmulti-converter.git
cd tonverk-elmulti-converter

# Install dependencies and run
uv venv
uv pip install -r requirements-gui.txt
uv run python3 elmconv_gui.py
```

### Build standalone app

```bash
uv pip install flet
flet pack elmconv_gui.py --name "Tonverk Elmulti Converter"
```

## Usage

1. **Select Output Folder** - Choose where converted files will be saved
2. **Configure Options** (optional):
   - Resample to 48 kHz (recommended)
   - Optimize loop points
   - Normalize audio levels
   - Add prefix to output names
3. **Select Input** - Choose EXS24/SFZ file(s) or a folder
4. Conversion starts automatically
5. Check the log for results, use **Copy Debug** for detailed output

## CLI Version

For command-line usage, see the main [README.md](README.md).

## License

MIT License - See [LICENSE](LICENSE) for details.
