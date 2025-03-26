import base64
import os

# --- Configuration ---
WIDTH = 1200  # Image width
HEIGHT = 675  # Image height
BG_COLOR = "#282a36"  # Aider code background color
PRIMARY_COLOR = "#14b014"  # Aider terminal green
TEXT_COLOR = "#FFFFFF"  # White for contrast
FONT_SIZE_LARGE = 110
FONT_SIZE_MEDIUM = 55
FONT_SIZE_SMALL = 30
OUTPUT_FILENAME = "aider_30k_stars_celebration.svg"

# Font families - SVG will try these in order. Prioritize Inter, then fall back.
FONT_FAMILY_BOLD = (
    "'Inter Bold', 'DejaVu Sans Bold', 'Arial Bold', 'Helvetica Bold', sans-serif-bold, sans-serif"
)
FONT_FAMILY_REGULAR = "'Inter', 'DejaVu Sans', 'Arial', 'Helvetica', sans-serif"
# Use Bold for Medium for consistency and visual weight
FONT_FAMILY_MEDIUM = FONT_FAMILY_BOLD

# --- Paths (Adjust if needed) ---
# Assumes the script is run from the root of the aider repo
LOGO_PATH = "aider/website/assets/logo.svg"

# --- Text Content ---
line1 = "Thank You!"
line2 = "30,000"
line3 = "GitHub Stars"
line4 = "github.com/Aider-AI/aider"

# --- Load and Encode Logo ---
logo_data_uri = None
logo_width = 200  # Default width from logo.svg
logo_height = 60  # Default height from logo.svg
try:
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo_content = f.read()
        encoded_logo = base64.b64encode(logo_content).decode("utf-8")
        logo_data_uri = f"data:image/svg+xml;base64,{encoded_logo}"
        print(f"Logo loaded and encoded from {LOGO_PATH}")
        # Optional: Could parse SVG to get width/height, but using defaults is simpler
    else:
        print(f"Warning: Logo not found at {LOGO_PATH}, skipping logo.")
except Exception as e:
    print(f"Warning: Could not load or encode logo: {e}")

# --- Calculate Positions ---
center_x = WIDTH / 2
logo_y_pos = HEIGHT * 0.15
logo_x_pos = center_x - (logo_width / 2)

# Adjust text start based on whether logo is present
text_start_y = (
    logo_y_pos + logo_height + 30 if logo_data_uri else HEIGHT * 0.2
)  # Slightly reduced gap

current_y = text_start_y

# Calculate Y positions for each line (using dominant-baseline="middle" for vertical centering)
line1_y = current_y + FONT_SIZE_MEDIUM / 2
current_y += FONT_SIZE_MEDIUM + 25  # Reduced gap
line2_y = current_y + FONT_SIZE_LARGE / 2
current_y += FONT_SIZE_LARGE + 10  # Reduced gap
line3_y = current_y + FONT_SIZE_MEDIUM / 2
# Removed large gap calculation here, line4_y is positioned from bottom

# Position line 4 relative to the bottom edge
line4_y = (
    HEIGHT - FONT_SIZE_SMALL - 25 + FONT_SIZE_SMALL / 2
)  # Position near bottom, slightly higher

# --- Generate SVG Content ---
svg_elements = []

# Background
svg_elements.append(f'<rect width="100%" height="100%" fill="{BG_COLOR}"/>')

# Logo
if logo_data_uri:
    svg_elements.append(
        f'<image href="{logo_data_uri}" x="{logo_x_pos}" y="{logo_y_pos}" '
        f'width="{logo_width}" height="{logo_height}" />'
    )

# Text Lines
svg_elements.append(
    f'<text x="{center_x}" y="{line1_y}" font-family="{FONT_FAMILY_MEDIUM}"'
    f' font-size="{FONT_SIZE_MEDIUM}" fill="{TEXT_COLOR}" text-anchor="middle"'
    f' dominant-baseline="middle">{line1}</text>'
)
svg_elements.append(
    f'<text x="{center_x}" y="{line2_y}" font-family="{FONT_FAMILY_BOLD}"'
    f' font-size="{FONT_SIZE_LARGE}" fill="{PRIMARY_COLOR}" text-anchor="middle"'
    f' dominant-baseline="middle" filter="url(#text-glow)">{line2}</text>'  # Added glow filter
)
svg_elements.append(
    f'<text x="{center_x}" y="{line3_y}" font-family="{FONT_FAMILY_MEDIUM}"'
    f' font-size="{FONT_SIZE_MEDIUM}" fill="{TEXT_COLOR}" text-anchor="middle"'
    f' dominant-baseline="middle">{line3}</text>'
)
svg_elements.append(
    f'<text x="{center_x}" y="{line4_y}" font-family="{FONT_FAMILY_REGULAR}"'
    f' font-size="{FONT_SIZE_SMALL}" fill="{TEXT_COLOR}" text-anchor="middle"'
    f' dominant-baseline="middle">{line4}</text>'
)

# Combine into final SVG
svg_content = f"""\
<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink">
  <defs>
    <filter id="text-glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="4 1" result="blur" />
      <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0.4 0" result="lighter-blur"/>
      <feComposite in="SourceGraphic" in2="lighter-blur" operator="over" />
    </filter>
  </defs>
  <style>
    /* Define font styles - adjust font family names as needed */
    @font-face {{
        font-family: 'Inter Bold'; /* Example */
        /* Add src url() if using web fonts, e.g.: */
        /* src: url(...) format(...); */
    }}
     @font-face {{
        font-family: 'Inter'; /* Example */
        /* Add src url() if using web fonts, e.g.: */
        /* src: url(...) format(...); */
    }}
     @font-face {{
        font-family: 'DejaVu Sans'; /* Example */
        /* Add src url() if using web fonts */
    }}
    /* Basic text styling */
    text {{
        font-weight: normal; /* Default */
    }}
    /* You can define classes here too if preferred */
    .font-bold {{ font-family: {FONT_FAMILY_BOLD}; font-weight: bold; }}
    /* Using bold for medium too */
    .font-medium {{ font-family: {FONT_FAMILY_BOLD}; font-weight: bold; }}
    .font-regular {{ font-family: {FONT_FAMILY_REGULAR}; }}

  </style>
  {''.join(svg_elements)}
</svg>
"""

# --- Save SVG Image ---
try:
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Celebration SVG image saved as '{OUTPUT_FILENAME}'")
except Exception as e:
    print(f"Error saving SVG image: {e}")
