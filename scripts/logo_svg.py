#!/usr/bin/env python3
"""
Script to generate an SVG logo for Aider with embedded font.
Reads the Glass_TTY_VT220.ttf font, subsets it to only include the letters needed,
and creates an SVG with the word "aider" in terminal green (#14b014) on a transparent background.
"""

import argparse
import base64
import os
import tempfile

from fontTools.subset import main as subset_main


def subset_font(font_path, text):
    """
    Create a subset of the font containing only the characters needed for the text.

    Args:
        font_path (str): Path to the TTF font file
        text (str): Text for which to extract characters

    Returns:
        bytes: The subsetted font data
    """
    # Create a temporary file to store the subset font
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    # Get unique characters from the text
    unique_chars = set(text.lower() + text.upper())

    # Create the subsetting command
    subset_args = [
        font_path,
        "--output-file=" + tmp_path,
        "--unicodes=" + ",".join([f"U+{ord(c):04X}" for c in unique_chars]),
        "--name-IDs=*",  # Keep all name records
        "--recalc-bounds",
        "--drop-tables=",  # Don't drop any tables by default
    ]

    # Run the subsetting
    subset_main(subset_args)

    # Read the subsetted font
    with open(tmp_path, "rb") as f:
        font_data = f.read()

    # Clean up the temporary file
    os.unlink(tmp_path)

    return font_data


def generate_svg_with_embedded_font(font_path, text="aider", color="#14b014", output_path=None):
    """
    Generate an SVG with embedded TTF font data.

    Args:
        font_path (str): Path to the TTF font file
        text (str): Text to display in the SVG
        color (str): Color of the text (hex format)
        output_path (str, optional): Path to save the SVG file, if None prints to stdout

    Returns:
        str: The SVG content
    """
    # Subset the font to only include the needed characters
    font_data = subset_font(font_path, text)

    # Encode the font data as base64
    font_base64 = base64.b64encode(font_data).decode("utf-8")

    # Calculate SVG dimensions based on text length
    # These values can be adjusted to modify the appearance
    char_width = 40
    width = len(text) * char_width
    height = 60
    text_x = width / 2  # Center point of the SVG width
    text_y = height * 0.62  # Center point of the SVG height

    # Create the SVG with embedded font and glow effect
    svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="glow" x="-40%" y="-30%" width="180%" height="160%">
      <feGaussianBlur stdDeviation="7 1" result="blur" />
      <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0.5 0" result="lighter-blur"/>
      <feComposite in="SourceGraphic" in2="lighter-blur" operator="over" />
    </filter>
  </defs>
  <style>
    @font-face {{
      font-family: 'GlassTTYVT220';
      src: url(data:font/truetype;charset=utf-8;base64,{font_base64}) format('truetype');
      font-weight: normal;
      font-style: normal;
    }}
    .logo-text {{
      font-family: 'GlassTTYVT220', monospace;
      font-size: 60px;
      fill: {color};
      text-anchor: middle; /* Center the text horizontally */
      dominant-baseline: middle; /* Center the text vertically */
      filter: url(#glow);
    }}
  </style>
  <text x="{text_x}" y="{text_y}" class="logo-text">{text}</text>
</svg>"""  # noqa

    # Save to file or print to stdout
    if output_path:
        with open(output_path, "w") as f:
            f.write(svg)
        print(f"SVG logo saved to {output_path}")

    return svg


def main():
    parser = argparse.ArgumentParser(description="Generate an SVG logo with embedded font")
    parser.add_argument(
        "--font",
        type=str,
        default="aider/website/assets/Glass_TTY_VT220.ttf",
        help="Path to the TTF font file",
    )
    parser.add_argument("--text", type=str, default="aider", help="Text to display in the SVG")
    parser.add_argument(
        "--color", type=str, default="#14b014", help="Color of the text (hex format)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="aider/website/assets/logo.svg",
        help="Path to save the SVG file",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print additional information about font subsetting"
    )

    args = parser.parse_args()

    # Make sure the font file exists
    if not os.path.exists(args.font):
        print(f"Error: Font file not found at {args.font}")
        return

    # Create output directory if it doesn't exist
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

    # Generate the SVG
    if args.verbose:
        print(f"Subsetting font {args.font} to include only characters for: {args.text}")

    svg = generate_svg_with_embedded_font(
        args.font, text=args.text, color=args.color, output_path=args.output
    )

    if args.verbose and args.output:
        # Calculate size savings
        original_size = os.path.getsize(args.font)
        output_size = len(svg.encode("utf-8"))
        print(f"Original font size: {original_size / 1024:.2f} KB")
        print(f"Output SVG size: {output_size / 1024:.2f} KB")


if __name__ == "__main__":
    main()
