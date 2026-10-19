# scripts/build_favicons.py
"""Generate every favicon variant from static/icons/icon-source.png."""
from pathlib import Path
from PIL import Image

SRC = Path("static/icons/icon-source.png")
ROOT = Path("static")
ICONS = ROOT / "icons"
ICONS.mkdir(parents=True, exist_ok=True)

source = Image.open(SRC).convert("RGBA")
if source.size != (512, 512):
    source = source.resize((512, 512), Image.LANCZOS)

# --- Multi-resolution .ico (16, 32, 48, 64, 128, 256) -------------------
# Windows Explorer, old browsers, and bookmarks use this.
ico_path = ROOT / "favicon.ico"
source.save(
    ico_path,
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print(f"Wrote {ico_path} (multi-res)")

# --- Individual PNGs -----------------------------------------------------
sizes = {
    "favicon-16x16.png":       16,
    "favicon-32x32.png":       32,
    "apple-touch-icon.png":   180,
    "icon-192.png":           192,
    "icon-512.png":           512,
}
for name, px in sizes.items():
    out = ICONS / name
    resized = source.resize((px, px), Image.LANCZOS)
    resized.save(out, "PNG", optimize=True)
    print(f"Wrote {out} ({px}x{px})")

# --- SVG favicon (optional, from the .ico's 32px raster) -----------------
# An SVG version is sharp at any zoom; this is a simplified "house on
# rounded square" trace, not a perfect vectorisation of the source.
svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#1d5144"/>
  <path d="M6 15.5 L16 6 L26 15.5 V26 a1 1 0 0 1 -1 1 H7 a1 1 0 0 1 -1 -1 Z"
        fill="none" stroke="#b9e4c8" stroke-width="2.2"
        stroke-linejoin="round"/>
  <path d="M13 27 V19 H19 V27" fill="none" stroke="#b9e4c8"
        stroke-width="2.2" stroke-linejoin="round"/>
</svg>
"""
(ICONS / "favicon.svg").write_text(svg)
print(f"Wrote {ICONS / 'favicon.svg'}")