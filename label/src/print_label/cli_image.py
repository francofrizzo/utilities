"""
Print images on a thermal cat printer.
Usage: print-image [OPTIONS] IMAGE

Examples:
  print-image photo.jpg
  print-image --dither floyd-steinberg photo.png
  print-image --preview logo.png
"""

import argparse
import asyncio
import sys
from pathlib import Path

import cv2
import numpy as np

from PIL import Image

from print_label.catprinter.ble import run_ble
from print_label.catprinter.cmds import cmds_print_img
from print_label.catprinter.img import (
    floyd_steinberg_dither,
    atkinson_dither,
    halftone_dither,
)


PRINTER_WIDTH = 384  # pixels

DITHER_ALGORITHMS = [
    'threshold',
    'floyd-steinberg',
    'atkinson',
    'halftone',
]


def prepare_image(image_path, dither='threshold'):
    """Load an image, resize to printer width, and binarize it.

    Returns an inverted boolean numpy array ready for printing.
    """
    im = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if im is None:
        print(f"Error: could not read image: {image_path}", file=sys.stderr)
        sys.exit(1)

    height, width = im.shape
    factor = PRINTER_WIDTH / width
    resized = cv2.resize(
        im,
        (PRINTER_WIDTH, int(height * factor)),
        interpolation=cv2.INTER_AREA,
    )

    if dither == 'floyd-steinberg':
        resized = floyd_steinberg_dither(resized)
        binarized = resized > 127
    elif dither == 'atkinson':
        resized = atkinson_dither(resized)
        binarized = resized > 127
    elif dither == 'halftone':
        resized = halftone_dither(resized)
        binarized = resized > 127
    else:  # threshold
        binarized = resized > 127

    # Trim leading/trailing blank rows to avoid excess padding
    inverted = ~binarized
    row_has_ink = np.any(inverted, axis=1)
    if row_has_ink.any():
        first = np.argmax(row_has_ink)
        last = len(row_has_ink) - np.argmax(row_has_ink[::-1])
        inverted = inverted[first:last]

    return inverted


def main():
    parser = argparse.ArgumentParser(
        description="Print images on thermal cat printer",
        epilog="Dithering algorithms:\n"
               "  floyd-steinberg Smooth error diffusion, best for photos (default)\n"
               "  atkinson        Higher contrast, good for mixed text+images\n"
               "  halftone        Classic newspaper dot pattern\n"
               "  threshold       Simple black/white cutoff, best for logos",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("image", help="Image file to print (PNG, JPG, etc.)")
    parser.add_argument("--dither", choices=DITHER_ALGORITHMS, default="floyd-steinberg",
                        help="Dithering algorithm (default: floyd-steinberg)")
    parser.add_argument("--preview", "-p", action="store_true",
                        help="Show preview instead of printing")
    parser.add_argument("--save", "-o", metavar="FILE",
                        help="Save processed image to file")
    parser.add_argument("--device", "-d", help="Printer BLE address or name")

    args = parser.parse_args()

    path = Path(args.image)
    if not path.exists():
        print(f"Error: file not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    img_data = prepare_image(path, dither=args.dither)

    if args.save or args.preview:
        preview = Image.fromarray((~img_data).astype('uint8') * 255)
        if args.save:
            preview.save(args.save)
            print(f"Saved to {args.save}")
        if args.preview:
            preview.show()
            return

    if args.save and not args.device:
        return

    commands = cmds_print_img(img_data, energy=0xffff, feed=48)
    asyncio.run(run_ble(commands, args.device))


if __name__ == "__main__":
    main()
