"""
Thermal printer label maker.
Usage: print-label [OPTIONS] TEXT

Font size is specified in units of 12pt (default: 6 = 72pt).

Examples:
  print-label "PANKO"
  print-label --small "Ingredient"
  print-label --large "WARNING"
  print-label --size 5 "Custom size"
  print-label "Main Label" --subtext "Subtitle here"
  print-label "Line 1\\nLine 2"
"""

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from print_label.catprinter.ble import run_ble
from print_label.catprinter.cmds import cmds_print_img
from print_label.catprinter.img import read_img


# ========== Constants ==========

PRINTER_WIDTH = 384  # pixels


def find_font():
    """Find the best available font on the system."""
    candidates = [
        # macOS
        ("/System/Library/Fonts/HelveticaNeue.ttc", 10, 0),
        ("/System/Library/Fonts/Helvetica.ttc", 1, 0),
        # Linux
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0, 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0, 0),
        # Windows
        ("C:/Windows/Fonts/arialbd.ttf", 0, 0),
        ("C:/Windows/Fonts/arial.ttf", 0, 0),
    ]
    for path, medium_idx, regular_idx in candidates:
        if Path(path).exists():
            return path, medium_idx, regular_idx
    raise RuntimeError("No suitable font found. Please install Helvetica, Liberation Sans, or Arial.")


FONT_PATH, FONT_INDEX_MEDIUM, FONT_INDEX_REGULAR = find_font()

SCALE_UNIT = 12  # 1 size unit = 12pt
SIZE_SMALL = 4
SIZE_NORMAL = 6
SIZE_LARGE = 8
SUBTEXT_RATIO = 0.75

PADDING = 20
SUPERSAMPLE = 4
MIN_FONT_SCALE = 0.75


# ========== Image Generation ==========

def _fit_single_line(text, font, max_width):
    """Fit a single logical line: word-wrap if needed. Returns (lines, overflow)."""
    text_width = font.getbbox(text)[2] - font.getbbox(text)[0]
    if text_width <= max_width:
        return [text], False

    words = text.split()
    if not words:
        return [text], False
    lines = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        if font.getbbox(test)[2] - font.getbbox(test)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)

    overflow = False
    for line in lines:
        line_width = font.getbbox(line)[2] - font.getbbox(line)[0]
        if line_width > max_width:
            print(f"Warning: \"{line}\" overflows the label width and will be clipped", file=sys.stderr)
            overflow = True

    return lines, overflow


def _fit_text(text, font_path, font_index, font_size, max_width):
    """Fit text within max_width: shrink font up to MIN_FONT_SCALE, then word-wrap.

    Supports explicit line breaks via \\n in the input text.
    """
    # Split on explicit line breaks
    segments = text.split('\n')

    font = ImageFont.truetype(font_path, size=font_size, index=font_index)

    # Find the widest segment to determine shrink factor
    widest = max(
        font.getbbox(seg)[2] - font.getbbox(seg)[0] for seg in segments
    )

    if widest > max_width:
        scale = max(MIN_FONT_SCALE, max_width / widest)
        shrunk_size = int(font_size * scale)
        font = ImageFont.truetype(font_path, size=shrunk_size, index=font_index)

    # Word-wrap each segment independently
    all_lines = []
    overflow = False
    for seg in segments:
        seg_lines, seg_overflow = _fit_single_line(seg, font, max_width)
        all_lines.extend(seg_lines)
        overflow = overflow or seg_overflow

    return font, all_lines, overflow


def _text_block_height(font, lines):
    """Total height of a block of text lines."""
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    spacing = int(line_h * 0.15)
    return line_h * len(lines) + spacing * max(0, len(lines) - 1), line_h, spacing


def create_label(text, subtext=None, size=SIZE_NORMAL):
    """Create a label image with text and optional subtext.

    Args:
        size: Label size in scale units (1 unit = 12pt). Default 6 (72pt).
    """
    main_size = int(size * SCALE_UNIT) * SUPERSAMPLE
    sub_size = int(main_size * SUBTEXT_RATIO)
    padding = PADDING * SUPERSAMPLE
    width = PRINTER_WIDTH * SUPERSAMPLE
    max_text_width = width - 2 * padding

    main_font, main_lines, overflow = _fit_text(
        text, FONT_PATH, FONT_INDEX_MEDIUM, main_size, max_text_width
    )
    main_block_h, main_line_h, main_spacing = _text_block_height(main_font, main_lines)

    total_height = main_block_h + padding * 2

    sub_font = sub_lines = None
    if subtext:
        sub_font, sub_lines, sub_overflow = _fit_text(
            subtext, FONT_PATH, FONT_INDEX_MEDIUM, sub_size, max_text_width
        )
        overflow = overflow or sub_overflow
        sub_block_h, sub_line_h, sub_spacing = _text_block_height(sub_font, sub_lines)
        total_height += sub_block_h + padding // 2

    img = Image.new("L", (width, total_height), color=255)
    draw = ImageDraw.Draw(img)

    y = padding
    for line in main_lines:
        bbox = main_font.getbbox(line)
        lw = bbox[2] - bbox[0]
        draw.text(((width - lw) // 2 - bbox[0], y - bbox[1]), line, font=main_font, fill=0)
        y += main_line_h + main_spacing

    if sub_lines:
        y = padding + main_block_h + padding // 2
        for line in sub_lines:
            bbox = sub_font.getbbox(line)
            lw = bbox[2] - bbox[0]
            draw.text(((width - lw) // 2 - bbox[0], y - bbox[1]), line, font=sub_font, fill=0)
            y += sub_line_h + sub_spacing

    return img, overflow


# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(
        description="Print labels on thermal printer",
        epilog="Size is in units of 12pt (default: 6 = 72pt)\n\n"
               "Examples:\n"
               "  print-label \"PANKO\"\n"
               "  print-label --small \"Ingredient\"\n"
               "  print-label --large \"WARNING\"\n"
               "  print-label --size 5 \"Custom size\"\n"
               "  print-label \"Main Label\" --subtext \"Subtitle here\"\n"
               "  print-label \"Line 1\\\\nLine 2\"",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("text", help="Main text to print")
    parser.add_argument("--subtext", "-s", help="Smaller subtitle text below main text")

    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument("--small", action="store_const", const=SIZE_SMALL, dest="size",
                           help=f"Use small font (size {SIZE_SMALL})")
    size_group.add_argument("--large", action="store_const", const=SIZE_LARGE, dest="size",
                           help=f"Use large font (size {SIZE_LARGE})")
    size_group.add_argument("--size", type=float, dest="size", metavar="N",
                           help=f"Custom size in units of {SCALE_UNIT}pt (default: {SIZE_NORMAL})")

    parser.add_argument("--preview", "-p", action="store_true",
                       help="Show preview instead of printing")
    parser.add_argument("--save", "-o", metavar="FILE",
                       help="Save label image to file")
    parser.add_argument("--device", "-d", help="Printer BLE address or name")

    args = parser.parse_args()

    if args.size is None:
        args.size = SIZE_NORMAL

    text = args.text.replace('\\n', '\n')
    subtext = args.subtext.replace('\\n', '\n') if args.subtext else args.subtext

    img, overflow = create_label(text, subtext=subtext, size=args.size)
    preview_img = img.resize(
        (PRINTER_WIDTH, img.size[1] // SUPERSAMPLE), Image.LANCZOS
    )

    if args.save:
        preview_img.save(args.save)
        print(f"Saved to {args.save}")

    if args.preview:
        preview_img.show()
        return

    if args.save and not args.device:
        return

    if overflow:
        answer = input("Text overflows the label. Print anyway? [y/N] ")
        if answer.lower() != 'y':
            print("Aborted.")
            return

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
        img.save(tmp_path)

    try:
        img_data = read_img(tmp_path, PRINTER_WIDTH, 'floyd-steinberg')
        commands = cmds_print_img(img_data, energy=0xffff)
        asyncio.run(run_ble(commands, args.device))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
