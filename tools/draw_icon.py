"""Draws the Rain Sense brand icon (water drop on a dark rounded square). Usage: python tools/draw_icon.py"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent.parent / "custom_components/rain_sense/brand"
S = 1024  # drawn large, scaled down for smooth edges


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=230, fill=(28, 28, 30, 255))
    d.ellipse((290, 400, 734, 844), fill=(10, 132, 255, 255))
    d.polygon([(512, 150), (320, 520), (704, 520)], fill=(10, 132, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


OUT.mkdir(exist_ok=True)
draw(256).save(OUT / "icon.png")
draw(512).save(OUT / "icon@2x.png")
