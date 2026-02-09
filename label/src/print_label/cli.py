"""
Thermal printer label maker.
Usage: print-label [OPTIONS] TEXT

Examples:
  print-label "PANKO"
  print-label --small "Ingredient"
  print-label --large "WARNING"
  print-label "Main Label" --subtext "Subtitle here"
"""

import argparse
import asyncio
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

FONT_SIZE_SMALL = 48
FONT_SIZE_NORMAL = 72
FONT_SIZE_LARGE = 96
SUBTEXT_SIZE = 32

PADDING = 20
SUPERSAMPLE = 2


# ========== Image Generation ==========

def create_label(text, subtext=None, size="normal"):
    """Create a label image with text and optional subtext."""
    size_map = {"small": FONT_SIZE_SMALL, "normal": FONT_SIZE_NORMAL, "large": FONT_SIZE_LARGE}
    main_size = size_map.get(size, FONT_SIZE_NORMAL) * SUPERSAMPLE
    sub_size = SUBTEXT_SIZE * SUPERSAMPLE
    padding = PADDING * SUPERSAMPLE
    width = PRINTER_WIDTH * SUPERSAMPLE

    main_font = ImageFont.truetype(FONT_PATH, size=main_size, index=FONT_INDEX_MEDIUM)

    main_bbox = main_font.getbbox(text)
    main_width = main_bbox[2] - main_bbox[0]
    main_height = main_bbox[3] - main_bbox[1]

    total_height = main_height + padding * 2

    if subtext:
        sub_font = ImageFont.truetype(FONT_PATH, size=sub_size, index=FONT_INDEX_REGULAR)
        sub_bbox = sub_font.getbbox(subtext)
        sub_height = sub_bbox[3] - sub_bbox[1]
        total_height += sub_height + padding // 2

    img = Image.new("L", (width, total_height), color=255)
    draw = ImageDraw.Draw(img)

    main_x = (width - main_width) // 2 - main_bbox[0]
    main_y = padding - main_bbox[1]
    draw.text((main_x, main_y), text, font=main_font, fill=0)

    if subtext:
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (width - sub_width) // 2 - sub_bbox[0]
        sub_y = main_y + main_height + padding // 2 - sub_bbox[1]
        draw.text((sub_x, sub_y), subtext, font=sub_font, fill=0)

    img = img.resize((PRINTER_WIDTH, total_height // SUPERSAMPLE), Image.LANCZOS)
    return img


# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(
        description="Print labels on thermal printer",
        epilog="Examples:\n"
               "  print-label \"PANKO\"\n"
               "  print-label --small \"Ingredient\"\n"
               "  print-label --large \"WARNING\"\n"
               "  print-label \"Main Label\" --subtext \"Subtitle here\"",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("text", help="Main text to print")
    parser.add_argument("--subtext", "-s", help="Smaller subtitle text below main text")

    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument("--small", action="store_const", const="small", dest="size",
                           help=f"Use small font ({FONT_SIZE_SMALL}pt)")
    size_group.add_argument("--large", action="store_const", const="large", dest="size",
                           help=f"Use large font ({FONT_SIZE_LARGE}pt)")

    parser.add_argument("--preview", "-p", action="store_true",
                       help="Show preview instead of printing")
    parser.add_argument("--save", "-o", metavar="FILE",
                       help="Save label image to file")
    parser.add_argument("--device", "-d", help="Printer BLE address or name")

    args = parser.parse_args()

    if args.size is None:
        args.size = "normal"

    img = create_label(args.text, subtext=args.subtext, size=args.size)

    if args.save:
        img.save(args.save)
        print(f"Saved to {args.save}")

    if args.preview:
        img.show()
        return

    if args.save and not args.device:
        return

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
        img.save(tmp_path)

    try:
        img_data = read_img(tmp_path, PRINTER_WIDTH, 'none')
        commands = cmds_print_img(img_data, energy=0xffff)
        asyncio.run(run_ble(commands, args.device))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
