#!/usr/bin/env python3
"""
Generate invitation image using a floral template and text from .env

Features:
- Hook divider lines (hook glyph is guaranteed via FONT_HOOK)
- Divider Y positions controlled via *_LINE_1_Y / *_LINE_2_Y (optional -> 1 line if LINE_2 empty)
- Message forced to exactly 2 lines via MESSAGE_LINE_1 + MESSAGE_LINE_2
- RSVP has its own font size option: RSVP_SIZE
- NEW: Small divider (typically under title / before details) fully controlled via .env
"""

import os
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

# ---------- Helpers ----------
def env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    return int(v) if v and v.strip() else default

def env_int_opt(key: str):
    v = os.getenv(key)
    if v is None:
        return None
    v = v.strip()
    return int(v) if v else None

def env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def env_color(key: str, default: str = "180,180,180"):
    raw = os.getenv(key, default)
    parts = [p.strip() for p in raw.split(",")]
    r, g, b = map(int, parts[:3])
    return (r, g, b, 255)

def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size=size)
    except Exception as e:
        print(f"[WARN] Could not load font '{path}' size {size}: {e}")
        return ImageFont.load_default()

def ensure_a4(img: Image.Image, dpi: int) -> Image.Image:
    target_w = int(round(8.27 * dpi))
    target_h = int(round(11.69 * dpi))
    if img.size != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return img

def draw_centered_multiline(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    center_x: int,
    top_y: int,
    fill=(40, 40, 40, 255),
    line_spacing_px: int = 10,
) -> int:
    y = top_y
    for line in text.split("\n"):
        if not line.strip():
            y += font.size + line_spacing_px
            continue
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((center_x - w // 2, y), line, font=font, fill=fill)
        y += h + line_spacing_px
    return y

def draw_hook_divider(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    width: int,
    color=(180, 180, 180, 255),
    thickness: int = 2,
    hook_char: str = "❦",
    hook_font: ImageFont.ImageFont | None = None,
    hook_gap: int = 22,
):
    """Draw a horizontal divider with a hook ornament in the center."""
    half = width // 2

    # Line segments
    draw.line([(center_x - half, y), (center_x - hook_gap, y)], fill=color, width=thickness)
    draw.line([(center_x + hook_gap, y), (center_x + half, y)], fill=color, width=thickness)

    if hook_font is None:
        hook_font = ImageFont.load_default()

    # If glyph missing, fallback to a safe char
    try:
        m = hook_font.getmask(hook_char)
        if m.size == (0, 0):
            hook_char = "•"
    except Exception:
        hook_char = "•"

    bbox = draw.textbbox((0, 0), hook_char, font=hook_font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    # Draw ornament slightly above the line
    draw.text((center_x - w // 2, y - int(h * 0.55)), hook_char, font=hook_font, fill=color)

def draw_divider_pair(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    width: int,
    color,
    thickness: int,
    hook_char: str,
    hook_font: ImageFont.ImageFont,
    hook_gap: int,
    line_1_y: int | None,
    line_2_y: int | None,
):
    """Draw 1 or 2 divider lines depending on whether Ys are provided."""
    if line_1_y is not None:
        draw_hook_divider(
            draw, center_x=center_x, y=line_1_y, width=width,
            color=color, thickness=thickness, hook_char=hook_char,
            hook_font=hook_font, hook_gap=hook_gap
        )
    if line_2_y is not None:
        draw_hook_divider(
            draw, center_x=center_x, y=line_2_y, width=width,
            color=color, thickness=thickness, hook_char=hook_char,
            hook_font=hook_font, hook_gap=hook_gap
        )

# ---------- Load config ----------
TEMPLATE = env_str("TEMPLATE_IMAGE")
OUTPUT = env_str("OUTPUT_IMAGE", "invite.png")
DPI = env_int("DPI", 300)

FONT_TITLE_PATH = env_str("FONT_TITLE")
FONT_BODY_PATH = env_str("FONT_BODY")
FONT_HOOK_PATH = env_str("FONT_HOOK", FONT_BODY_PATH)

TITLE_SIZE = env_int("TITLE_SIZE", 120)
BODY_SIZE = env_int("BODY_SIZE", 52)
SMALL_SIZE = env_int("SMALL_SIZE", 44)
HOOK_SIZE = env_int("HOOK_SIZE", 34)

# RSVP size (defaults to BODY_SIZE if not set)
RSVP_SIZE = env_int("RSVP_SIZE", BODY_SIZE)

# Text
INTRO = env_str("INTRO_TEXT")
TITLE = f"{env_str('TITLE_LINE_1')}\n{env_str('TITLE_LINE_2')}"
DETAILS = "\n".join([env_str("DETAIL_LINE_1"), env_str("DETAIL_LINE_2"), env_str("DETAIL_LINE_3")])
MESSAGE = f"{env_str('MESSAGE_LINE_1')}\n{env_str('MESSAGE_LINE_2')}"
SIGN = f"{env_str('SIGN_LINE_1')}\n{env_str('SIGN_LINE_2')}"
RSVP = env_str("RSVP_TEXT")

# Positions
Y_INTRO = env_int("Y_INTRO", 780)
Y_TITLE = env_int("Y_TITLE", 900)
Y_DETAILS = env_int("Y_DETAILS", 1320)
Y_MESSAGE = env_int("Y_MESSAGE", 1840)
Y_SIGN = env_int("Y_SIGN", 2320)
Y_RSVP = env_int("Y_RSVP", 3000)

# Divider style (global / default)
LINE_WIDTH = env_int("LINE_WIDTH", 900)
LINE_THICKNESS = env_int("LINE_THICKNESS", 2)
LINE_COLOR = env_color("LINE_COLOR")
HOOK_GAP = env_int("HOOK_GAP", 22)
HOOK_CHAR = env_str("HOOK_CHAR", "❦")

# Divider Y options (two per divider)
DETAILS_DIVIDER_LINE_1_Y = env_int_opt("DETAILS_DIVIDER_LINE_1_Y")
DETAILS_DIVIDER_LINE_2_Y = env_int_opt("DETAILS_DIVIDER_LINE_2_Y")
MESSAGE_DIVIDER_LINE_1_Y = env_int_opt("MESSAGE_DIVIDER_LINE_1_Y")
MESSAGE_DIVIDER_LINE_2_Y = env_int_opt("MESSAGE_DIVIDER_LINE_2_Y")

# NEW: Small divider (typically under title / before details), fully in .env
SMALL_DIVIDER_WIDTH = env_int("SMALL_DIVIDER_WIDTH", 150)
SMALL_DIVIDER_LINE_1_Y = env_int_opt("SMALL_DIVIDER_LINE_1_Y")
SMALL_DIVIDER_LINE_2_Y = env_int_opt("SMALL_DIVIDER_LINE_2_Y")

# Optional overrides for the small divider (fallback to global)
SMALL_DIVIDER_THICKNESS = env_int("SMALL_DIVIDER_THICKNESS", LINE_THICKNESS)
SMALL_DIVIDER_COLOR = env_color("SMALL_DIVIDER_COLOR", "180,180,180")
SMALL_DIVIDER_HOOK_GAP = env_int("SMALL_DIVIDER_HOOK_GAP", HOOK_GAP)
SMALL_DIVIDER_HOOK_CHAR = env_str("SMALL_DIVIDER_HOOK_CHAR", HOOK_CHAR)

# Colors
TEXT_COLOR = (45, 45, 45, 255)

# ---------- Build ----------
img = Image.open(TEMPLATE).convert("RGBA")
img = ensure_a4(img, DPI)
draw = ImageDraw.Draw(img)
cx = img.size[0] // 2

# Fonts
font_title = load_font(FONT_TITLE_PATH, TITLE_SIZE)
font_body = load_font(FONT_BODY_PATH, BODY_SIZE)
font_small = load_font(FONT_BODY_PATH, SMALL_SIZE)
font_hook = load_font(FONT_HOOK_PATH, HOOK_SIZE)

# RSVP font
font_rsvp = load_font(FONT_BODY_PATH, RSVP_SIZE)

# Intro
draw_centered_multiline(draw, INTRO, font_small, cx + 50, Y_INTRO, fill=TEXT_COLOR, line_spacing_px=10)

# Title
draw_centered_multiline(draw, TITLE, font_title, cx + 50, Y_TITLE, fill=TEXT_COLOR, line_spacing_px=6)

# NEW: Small divider (under title / before details) - controlled by .env
# If SMALL_DIVIDER_LINE_1_Y is empty, nothing will be drawn.
draw_divider_pair(
    draw,
    center_x=cx + 50,
    width=SMALL_DIVIDER_WIDTH,
    color=SMALL_DIVIDER_COLOR,
    thickness=SMALL_DIVIDER_THICKNESS,
    hook_char=SMALL_DIVIDER_HOOK_CHAR,
    hook_font=font_hook,
    hook_gap=SMALL_DIVIDER_HOOK_GAP,
    line_1_y=SMALL_DIVIDER_LINE_1_Y,
    line_2_y=SMALL_DIVIDER_LINE_2_Y,
)

# Details
draw_centered_multiline(draw, DETAILS, font_body, cx + 50, Y_DETAILS, fill=TEXT_COLOR, line_spacing_px=14)

# Divider(s) after details
draw_divider_pair(
    draw,
    center_x=cx + 50,
    width=LINE_WIDTH,
    color=LINE_COLOR,
    thickness=LINE_THICKNESS,
    hook_char=HOOK_CHAR,
    hook_font=font_hook,
    hook_gap=HOOK_GAP,
    line_1_y=DETAILS_DIVIDER_LINE_1_Y,
    line_2_y=DETAILS_DIVIDER_LINE_2_Y,
)

# Message (exactly 2 lines)
draw_centered_multiline(draw, MESSAGE, font_small, cx + 50, Y_MESSAGE, fill=TEXT_COLOR, line_spacing_px=14)

# Divider(s) after message
draw_divider_pair(
    draw,
    center_x=cx + 50,
    width=LINE_WIDTH,
    color=LINE_COLOR,
    thickness=LINE_THICKNESS,
    hook_char=HOOK_CHAR,
    hook_font=font_hook,
    hook_gap=HOOK_GAP,
    line_1_y=MESSAGE_DIVIDER_LINE_1_Y,
    line_2_y=MESSAGE_DIVIDER_LINE_2_Y,
)

# Signature
draw_centered_multiline(draw, SIGN, font_body, cx + 50, Y_SIGN, fill=TEXT_COLOR, line_spacing_px=12)

# RSVP (uses RSVP_SIZE via font_rsvp)
draw_centered_multiline(draw, RSVP, font_rsvp, cx + 50, Y_RSVP, fill=TEXT_COLOR, line_spacing_px=10)

img.save(OUTPUT, "PNG")
print(f"[OK] Wrote {OUTPUT} ({img.size[0]}x{img.size[1]} px @ ~{DPI}dpi)")
