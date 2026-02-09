# print-label

Thermal printer label maker for Bluetooth cat printers. Create beautiful labels with Helvetica Neue font.

## Features

- **Simple CLI** — one command to print labels
- **Multiple sizes** — small (48pt), normal (72pt), large (96pt)
- **Subtitles** — add smaller text below the main label
- **Preview mode** — see before you print
- **Cross-platform** — works on macOS, Linux, and Windows

## Install

### Homebrew

```bash
brew install francofrizzo/tap/print-label
```

### Manual

```bash
git clone https://github.com/francofrizzo/utilities.git
cd utilities/label
pip install .
```

### Dependencies

- Python 3.8+
- Pillow (image processing)
- bleak (Bluetooth Low Energy)
- numpy, opencv-python (image dithering)

## Usage

### Basic labels

```bash
# Normal size (72pt)
print-label "PANKO"

# Small font (48pt)
print-label --small "Ingredient"

# Large font (96pt)
print-label --large "WARNING"
```

### With subtitles

```bash
print-label "BREAD CRUMBS" --subtext "Japanese Style"
print-label "OLIVE OIL" -s "Extra Virgin"
```

### Preview and save

```bash
# Preview without printing
print-label "TEST" --preview

# Save to file
print-label "PANKO" --save panko.png

# Both
print-label "LABEL" --preview --save label.png
```

### Options

| Option | Description |
|---|---|
| `--small` | Use 48pt font |
| `--large` | Use 96pt font |
| `--subtext TEXT`, `-s TEXT` | Add smaller subtitle below main text |
| `--preview`, `-p` | Show preview without printing |
| `--save FILE`, `-o FILE` | Save label image to file |
| `--device ADDR`, `-d ADDR` | Specify printer BLE address |

## Supported Printers

Cat printers (GB01, GB02, GB03, GT01, MX05, MX06, MX08, MX10, YT01) and similar Bluetooth thermal printers.

## Font

Uses Helvetica Neue Medium on macOS, with automatic fallbacks:
- **Linux**: Liberation Sans Bold
- **Windows**: Arial Bold

## How it works

1. Renders text at 2x resolution for quality
2. Downsamples with antialiasing
3. Sends to printer via Bluetooth Low Energy
4. Uses run-length encoding for efficient transmission

## License

MIT
