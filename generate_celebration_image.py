import os

from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---
WIDTH = 1200  # Twitter card image width
HEIGHT = 675  # Twitter card image height
BG_COLOR = "#282a36"  # Aider code background color
PRIMARY_COLOR = "#14b014"  # Aider terminal green
TEXT_COLOR = "#FFFFFF"  # White for contrast
FONT_SIZE_LARGE = 110
FONT_SIZE_MEDIUM = 55
FONT_SIZE_SMALL = 30
OUTPUT_FILENAME = "aider_30k_stars_celebration.png"

# --- Paths (Adjust if needed) ---
# Assumes the script is run from the root of the aider repo
LOGO_PATH = "aider/website/assets/logo.png"  # NEEDS TO BE PNG, not SVG!
# Try to find a suitable bold font. Adjust path if necessary, or install one.
# Common locations/names:
FONT_PATHS_BOLD = [
    "DejaVuSans-Bold.ttf",  # Common on Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "Arial Bold.ttf",  # Common on Windows/macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "arialbd.ttf",
]
FONT_PATHS_REGULAR = [
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "arial.ttf",
]


# --- Helper Function to Find Font ---
def find_font(font_paths, default_size):
    for path in font_paths:
        try:
            return ImageFont.truetype(path, default_size)
        except IOError:
            continue  # Try next path
    print(f"Warning: Could not find any of the preferred fonts: {font_paths}. Using default.")
    # Pillow's default font doesn't support sizing well, return None to handle later
    return None


# --- Load Fonts ---
font_large = find_font(FONT_PATHS_BOLD, FONT_SIZE_LARGE)
font_medium = find_font(FONT_PATHS_BOLD, FONT_SIZE_MEDIUM)
font_small = find_font(FONT_PATHS_REGULAR, FONT_SIZE_SMALL)

# Use Pillow's basic default only if absolutely necessary (will look bad)
if not font_large:
    font_large = ImageFont.load_default()
if not font_medium:
    font_medium = ImageFont.load_default()
if not font_small:
    font_small = ImageFont.load_default()


# --- Create Base Image ---
image = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
draw = ImageDraw.Draw(image)

# --- Load and Place Logo (Optional) ---
logo_img = None
logo_height = 0
logo_y_pos = HEIGHT * 0.15  # Start logo about 15% down
try:
    if os.path.exists(LOGO_PATH):
        logo_img = Image.open(LOGO_PATH)
        # Resize logo to fit nicely, maintaining aspect ratio
        max_logo_h = 120
        if logo_img.height > max_logo_h:
            ratio = max_logo_h / logo_img.height
            new_w = int(logo_img.width * ratio)
            logo_img = logo_img.resize((new_w, max_logo_h), Image.Resampling.LANCZOS)

        logo_height = logo_img.height
        logo_x = (WIDTH - logo_img.width) // 2
        # Paste logo, handling transparency if PNG has alpha channel
        if logo_img.mode == "RGBA":
            image.paste(logo_img, (logo_x, int(logo_y_pos)), logo_img)
        else:
            image.paste(logo_img, (logo_x, int(logo_y_pos)))
        print(f"Logo loaded from {LOGO_PATH}")
    else:
        print(f"Info: Logo not found at {LOGO_PATH}, skipping logo.")
        logo_y_pos = HEIGHT * 0.1  # Start text higher if no logo
except Exception as e:
    print(f"Warning: Could not load or process logo: {e}")
    logo_img = None
    logo_y_pos = HEIGHT * 0.1  # Start text higher if no logo

# --- Text Content ---
line1 = "Thank You!"
line2 = "30,000"
line3 = "GitHub Stars"
line4 = "github.com/Aider-AI/aider"

# --- Calculate Text Positions ---
center_x = WIDTH / 2
current_y = logo_y_pos + logo_height + 40  # Start text below logo (or top if no logo)

# --- Draw Text ---
# Line 1: "Thank You!"
draw.text((center_x, current_y), line1, fill=TEXT_COLOR, font=font_medium, anchor="mt")
current_y += FONT_SIZE_MEDIUM + 30

# Line 2: "30,000"
draw.text((center_x, current_y), line2, fill=PRIMARY_COLOR, font=font_large, anchor="mt")
current_y += FONT_SIZE_LARGE + 15

# Line 3: "GitHub Stars"
draw.text((center_x, current_y), line3, fill=TEXT_COLOR, font=font_medium, anchor="mt")
current_y += FONT_SIZE_MEDIUM + 60

# Line 4: Repo URL (smaller at bottom)
draw.text(
    (center_x, HEIGHT - FONT_SIZE_SMALL - 30), line4, fill=TEXT_COLOR, font=font_small, anchor="mb"
)


# --- Save Image ---
try:
    image.save(OUTPUT_FILENAME)
    print(f"Celebration image saved as '{OUTPUT_FILENAME}'")
except Exception as e:
    print(f"Error saving image: {e}")
