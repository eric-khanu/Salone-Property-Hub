"""Generate a 512x512 brand icon for SL Property Hub."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SIZE = 512
OUT = Path("static/icons/icon-source.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

# Brand colours (from output.css :root)
GREEN = (29, 81, 68)      # --green  #1d5144
MINT  = (185, 228, 200)   # #b9e4c8  (hero h1 span colour)

img = Image.new("RGBA", (SIZE, SIZE), GREEN)
draw = ImageDraw.Draw(img)

# Draw a bold house using the ⌂ glyph — fall back to a drawn shape if
# no font on the system has it.
try:
    font = ImageFont.truetype("seguisym.ttf", 360)  # Windows
except OSError:
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 360)  # Linux/macOS
    except OSError:
        font = ImageFont.load_default()
        font.size = 360

text = "⌂"
bbox = draw.textbbox((0, 0), text, font=font)
w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text(
    ((SIZE - w) / 2 - bbox[0], (SIZE - h) / 2 - bbox[1]),
    text, font=font, fill=MINT,
)

img.save(OUT, "PNG")
print(f"Wrote {OUT} ({SIZE}x{SIZE})")