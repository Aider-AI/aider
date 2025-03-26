#!/usr/bin/env python
"""
Generate a celebratory SVG image for Aider reaching 30,000 GitHub stars.
This creates a shareable social media graphic with confetti animation.
"""

import argparse
import base64
import math
import os
import random
from pathlib import Path

# Default colors for the celebration image
AIDER_GREEN = "#14b014"
AIDER_BLUE = "#4C6EF5"
DARK_COLOR = "#212529"
LIGHT_COLOR = "#F8F9FA"
GOLD_COLOR = "#f1c40f"

# Default dimensions for social sharing
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 630


def embed_font():
    """Returns base64 encoded font data for the GlassTTYVT220 font."""
    # Path to the font file
    font_path = (
        Path(__file__).parent.parent / "aider" / "website" / "assets" / "Glass_TTY_VT220.ttf"
    )

    # If font file doesn't exist, return empty string
    if not font_path.exists():
        print(f"Warning: Font file not found at {font_path}")
        return ""

    # Read and encode the font file
    with open(font_path, "rb") as f:
        font_data = f.read()

    # Return base64 encoded font data
    return base64.b64encode(font_data).decode("utf-8")


def generate_confetti(count=150, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Generate SVG confetti elements for the celebration."""
    confetti = []
    colors = [AIDER_GREEN, AIDER_BLUE, GOLD_COLOR, "#e74c3c", "#9b59b6", "#3498db", "#2ecc71"]

    # Define text safe zones
    # Main content safe zone (centered area)
    safe_zone_x_min = width * 0.2
    safe_zone_x_max = width * 0.8
    safe_zone_y_min = height * 0.25
    safe_zone_y_max = height * 0.75

    # Footer safe zone (for GitHub URL)
    footer_safe_zone_x_min = width * 0.25
    footer_safe_zone_x_max = width * 0.75
    footer_safe_zone_y_min = height - 100  # 100px from bottom
    footer_safe_zone_y_max = height  # Bottom of image

    # Keep trying until we have enough confetti pieces
    attempts = 0
    confetti_count = 0

    while confetti_count < count and attempts < count * 3:
        attempts += 1

        # Generate random position
        x = random.randint(0, width)
        y = random.randint(0, height)

        # Skip if the position is in either of the safe zones
        if (
            (safe_zone_x_min < x < safe_zone_x_max) and (safe_zone_y_min < y < safe_zone_y_max)
        ) or (
            (footer_safe_zone_x_min < x < footer_safe_zone_x_max)
            and (footer_safe_zone_y_min < y < footer_safe_zone_y_max)
        ):
            continue

        confetti_count += 1
        size = random.randint(5, 15)
        color = random.choice(colors)
        rotation = random.randint(0, 360)
        delay = random.uniform(0, 2)
        duration = random.uniform(1, 3)

        # Randomly choose between rect (square), circle, and star shapes
        shape_type = random.choice(["rect", "circle", "star"])

        if shape_type == "rect":
            shape = f"""<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{color}"
                    transform="rotate({rotation}, {x + size/2}, {y + size/2})">
                <animate attributeName="opacity" from="1" to="0" dur="{duration}s" begin="{delay}s" repeatCount="indefinite" />
                <animate attributeName="y" from="{y}" to="{y + random.randint(200, 400)}" dur="{duration}s" begin="{delay}s" repeatCount="indefinite" />
            </rect>"""
        elif shape_type == "circle":
            shape = f"""<circle cx="{x}" cy="{y}" r="{size/2}" fill="{color}">
                <animate attributeName="opacity" from="1" to="0" dur="{duration}s" begin="{delay}s" repeatCount="indefinite" />
                <animate attributeName="cy" from="{y}" to="{y + random.randint(200, 400)}" dur="{duration}s" begin="{delay}s" repeatCount="indefinite" />
            </circle>"""
        else:  # star
            # Create a simple 5-point star
            points = []
            for j in range(5):
                angle = j * 2 * 3.14159 / 5
                x_point = x + (size * 0.5) * math.cos(angle)
                y_point = y + (size * 0.5) * math.sin(angle)
                points.append(f"{x_point},{y_point}")

                # Inner points of the star
                inner_angle = angle + 3.14159 / 5
                inner_x = x + (size * 0.2) * math.cos(inner_angle)
                inner_y = y + (size * 0.2) * math.sin(inner_angle)
                points.append(f"{inner_x},{inner_y}")

            points_str = " ".join(points)
            shape = f"""<polygon points="{points_str}" fill="{color}"
                    transform="rotate({rotation}, {x}, {y})">
                <animate attributeName="opacity" from="1" to="0" dur="{duration}s" begin="{delay}s" repeatCount="indefinite" />
                <animate attributeName="transform" from="rotate({rotation}, {x}, {y})" to="rotate({rotation + 360}, {x}, {y})" dur="{duration*2}s" begin="{delay}s" repeatCount="indefinite" />
                <animate attributeName="cy" from="{y}" to="{y + random.randint(200, 400)}" dur="{duration}s" begin="{delay}s" repeatCount="indefinite" />
            </polygon>"""

        confetti.append(shape)

    return "\n".join(confetti)


def generate_celebration_svg(output_path=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Generate a celebratory SVG for 30K GitHub stars."""

    # Font embedding
    font_data = embed_font()
    font_face = f"""
    @font-face {{
        font-family: 'GlassTTYVT220';
        src: url(data:font/truetype;charset=utf-8;base64,{font_data}) format('truetype');
        font-weight: normal;
        font-style: normal;
    }}
    """ if font_data else ""

    # Generate confetti elements
    confetti = generate_confetti(count=150, width=width, height=height)

    # Create the SVG content
    svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="10" result="blur" />
      <feComponentTransfer in="blur" result="glow">
        <feFuncA type="linear" slope="0.7" intercept="0" />
      </feComponentTransfer>
      <feComposite in="SourceGraphic" in2="glow" operator="over" />
    </filter>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#121212" />
      <stop offset="100%" style="stop-color:#212529" />
    </linearGradient>
    <clipPath id="rounded-rect">
      <rect x="0" y="0" width="{width}" height="{height}" rx="20" ry="20" />
    </clipPath>
  </defs>
  <style>
    {font_face}
    .main-bg {{ fill: url(#bg-gradient); }}
    .aider-logo {{ font-family: 'GlassTTYVT220', monospace; font-size: 120px; fill: {AIDER_GREEN}; text-anchor: middle; filter: url(#glow); }}
    .stars-text {{ font-family: 'GlassTTYVT220', monospace; font-size: 72px; fill: {GOLD_COLOR}; text-anchor: middle; filter: url(#glow); }}
    .tagline {{ font-family: sans-serif; font-size: 32px; fill: {LIGHT_COLOR}; text-anchor: middle; }}
    .footer {{ font-family: sans-serif; font-size: 24px; fill: {LIGHT_COLOR}; text-anchor: middle; opacity: 0.8; }}
  </style>

  <g clip-path="url(#rounded-rect)">
    <!-- Background with pattern -->
    <rect class="main-bg" x="0" y="0" width="{width}" height="{height}" />

    <!-- Pattern overlay -->
    <rect width="{width}" height="{height}" fill="url(#bg-gradient)" opacity="0.9" />

    <!-- Confetti animation -->
    {confetti}

    <!-- Main content -->
    <text x="{width/2}" y="{height/2 - 100}" class="aider-logo">aider</text>
    <text x="{width/2}" y="{height/2 + 20}" class="stars-text">30,000 GitHub stars!</text>
    <text x="{width/2}" y="{height/2 + 100}" class="tagline">Thank you to our amazing community!</text>
    <text x="{width/2}" y="{height - 50}" class="footer">github.com/Aider-AI/aider</text>

  </g>
</svg>
"""

    # Write to file if output path is specified
    if output_path:
        with open(output_path, "w") as f:
            f.write(svg_content)
        print(f"Celebration SVG saved to {output_path}")

    return svg_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a celebration SVG for Aider's 30K GitHub stars"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="aider-30k-stars.svg",
        help="Output file path (default: aider-30k-stars.svg)",
    )
    parser.add_argument(
        "--width",
        "-w",
        type=int,
        default=DEFAULT_WIDTH,
        help=f"Image width in pixels (default: {DEFAULT_WIDTH})",
    )
    parser.add_argument(
        "--height",
        "-ht",
        type=int,
        default=DEFAULT_HEIGHT,
        help=f"Image height in pixels (default: {DEFAULT_HEIGHT})",
    )
    args = parser.parse_args()

    # Generate the SVG
    generate_celebration_svg(args.output, args.width, args.height)
