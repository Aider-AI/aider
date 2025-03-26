import base64
import os

# --- Configuration ---
WIDTH = 1200  # Image width
HEIGHT = 675  # Image height
BG_COLOR = "#282a36"  # Aider code background color
PRIMARY_COLOR = "#14b014"  # Aider terminal green
TEXT_COLOR = "#FFFFFF"  # White for contrast
GRID_COLOR = "#3b3d4a"  # Slightly lighter than background for grid pattern
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
line1 = "Thank You to Our Community!"
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

# Background with terminal-like pattern and subtle code
svg_elements.append(f"""<defs>
    <pattern id="grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
        <rect width="40" height="40" fill="{BG_COLOR}"/>
        <path d="M 40 0 L 0 0 0 40" stroke="{GRID_COLOR}" stroke-width="0.5" fill="none" opacity="0.3"/>
    </pattern>
    
    <!-- GitHub octocat logo -->
    <g id="github-logo">
        <path fill="#FFFFFF" d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
    </g>
    
    <!-- More complex glow filter -->
    <filter id="enhanced-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur in="SourceAlpha" stdDeviation="8" result="blur1"/>
        <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur2"/>
        <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur3"/>
        <feMerge result="merged-blur">
            <feMergeNode in="blur1"/>
            <feMergeNode in="blur2"/>
            <feMergeNode in="blur3"/>
        </feMerge>
        <feColorMatrix in="merged-blur" type="matrix" values="1 0 0 0 0 
                                                             0 1 0 0 0 
                                                             0 0 1 0 0 
                                                             0 0 0 0.8 0" result="glow"/>
        <feComposite in="SourceGraphic" in2="glow" operator="over"/>
    </filter>
    
    <!-- Terminal code background pattern -->
    <pattern id="code-pattern" width="600" height="400" patternUnits="userSpaceOnUse" patternTransform="scale(0.5)">
        <rect width="600" height="400" fill="{BG_COLOR}"/>
        <text x="20" y="30" font-family="'Fira Code', monospace" font-size="14" fill="#4CAF50" opacity="0.15">$ git commit -m "Initial commit"</text>
        <text x="20" y="60" font-family="'Fira Code', monospace" font-size="14" fill="#4CAF50" opacity="0.15">$ aider --model gpt-4</text>
        <text x="20" y="90" font-family="'Fira Code', monospace" font-size="14" fill="#4CAF50" opacity="0.15">def hello_world():</text>
        <text x="40" y="120" font-family="'Fira Code', monospace" font-size="14" fill="#4CAF50" opacity="0.15">print("Hello from Aider!")</text>
    </pattern>
</defs>""")

# Background with code pattern
svg_elements.append(f'<rect width="100%" height="100%" fill="url(#code-pattern)"/>')

# Terminal-like border with more authentic styling
svg_elements.append(
    f'<rect x="30" y="30" width="{WIDTH-60}" height="{HEIGHT-60}" fill="none"'
    f' stroke="{PRIMARY_COLOR}" stroke-width="3" rx="6" ry="6" stroke-dasharray="5,3" opacity="0.8"/>'
)

# Add GitHub logo in corner
svg_elements.append(
    f'<use href="#github-logo" x="{WIDTH-80}" y="50" width="40" height="40" opacity="0.8"/>'
)

# Logo with glow
if logo_data_uri:
    svg_elements.append(
        f'<image href="{logo_data_uri}" x="{logo_x_pos}" y="{logo_y_pos}" '
        f'width="{logo_width}" height="{logo_height}" filter="url(#logo-glow)" />'
    )

# Text Lines
# Adjust font size for longer text
svg_elements.append(
    f'<text x="{center_x}" y="{line1_y - 15}" font-family="{FONT_FAMILY_MEDIUM}"'
    f' font-size="{FONT_SIZE_MEDIUM - 5}" fill="{TEXT_COLOR}" text-anchor="middle"'
    f' dominant-baseline="middle">{line1}</text>'
)
# Add animated star decorations around the 30,000 number
star_colors = ["#FFD700", "#FFA500", "#FF6347", "#FF69B4", "#00FFFF"]
for i in range(8):
    # Left side stars
    x_left = center_x - 320 + (i * 70)
    y_left = line2_y - 60 + (i % 3 * 10)
    size_factor = 0.4 + (i % 4) * 0.2  # More size variation
    rotation = i * 15  # Different rotations
    color = star_colors[i % len(star_colors)]
    svg_elements.append(
        f'<path d="M 0,0 L 5,-15 L 0,-5 L -5,-15 L 0,0 Z" fill="{color}" opacity="0.9" '
        f'transform="translate({x_left}, {y_left}) scale({size_factor}) rotate({rotation})" filter="url(#enhanced-glow)">'
        f'<animate attributeName="opacity" values="0.7;1;0.7" dur="{3 + i%2}s" repeatCount="indefinite"/>'
        f'<animateTransform attributeName="transform" type="scale" values="{size_factor};{size_factor*1.3};{size_factor}" dur="{4 + i%3}s" repeatCount="indefinite"/>'
        f'</path>'
    )

    # Right side stars
    x_right = center_x + 180 + (i * 70)
    y_right = line2_y - 50 - (i % 3 * 10)
    size_factor = 0.3 + (i % 4) * 0.25  # More size variation
    rotation = i * 20  # Different rotations
    color = star_colors[(i+2) % len(star_colors)]
    svg_elements.append(
        f'<path d="M 0,0 L 5,-15 L 0,-5 L -5,-15 L 0,0 Z" fill="{color}" opacity="0.9" '
        f'transform="translate({x_right}, {y_right}) scale({size_factor}) rotate({rotation})" filter="url(#enhanced-glow)">'
        f'<animate attributeName="opacity" values="0.7;1;0.7" dur="{2 + i%3}s" repeatCount="indefinite"/>'
        f'<animateTransform attributeName="transform" type="scale" values="{size_factor};{size_factor*1.4};{size_factor}" dur="{3 + i%2}s" repeatCount="indefinite"/>'
        f'</path>'
    )

# Enhanced 30,000 number with multi-layer glow and GitHub reference
svg_elements.append(
    f'<text x="{center_x}" y="{line2_y}" font-family="{FONT_FAMILY_BOLD}"'
    f' font-size="{FONT_SIZE_LARGE}" fill="{PRIMARY_COLOR}" text-anchor="middle"'
    f' dominant-baseline="middle" filter="url(#enhanced-glow)">{line2}</text>'
)

# Add GitHub reference text
svg_elements.append(
    f'<text x="{center_x}" y="{line2_y + 40}" font-family="{FONT_FAMILY_REGULAR}"'
    f' font-size="20" fill="#FFFFFF" text-anchor="middle"'
    f' dominant-baseline="middle" opacity="0.8">GitHub Stars</text>'
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
    <!-- Enhanced glow for numbers -->
    <filter id="number-glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="6 2" result="blur" />
      <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0.6 0" result="lighter-blur"/>
      <feComposite in="SourceGraphic" in2="lighter-blur" operator="over" />
    </filter>
    
    <!-- Original glow filter (renamed) -->
    <filter id="text-glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="4 1" result="blur" />
      <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0.4 0" result="lighter-blur"/>
      <feComposite in="SourceGraphic" in2="lighter-blur" operator="over" />
    </filter>
    
    <!-- Logo glow filter -->
    <filter id="logo-glow" x="-40%" y="-30%" width="180%" height="160%">
      <feGaussianBlur stdDeviation="8 2" result="blur" />
      <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0.5 0" result="lighter-blur"/>
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
