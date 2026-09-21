"""
Generate the PWA icon set into static/icons/.

Run from the project root after changing the brand colour or monogram:

    python tools/generate_icons.py

Chrome needs a 192px and a 512px icon before it will offer to install the app,
and a separate "maskable" pair so Android can crop the icon to the launcher's
own shape without clipping the artwork. The maskable variants keep all content
inside the middle 80% safe zone and bleed the background to the edges.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BRAND = (234, 88, 12)          # #ea580c, the app's existing orange
BRAND_DARK = (154, 52, 18)     # #9a3412
WHITE = (255, 255, 255)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'static' / 'icons'

FONT_CANDIDATES = [
    'C:/Windows/Fonts/arialbd.ttf',
    'C:/Windows/Fonts/arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
]


def _load_font(size):
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _draw_gear(draw, centre, radius, colour, teeth=8):
    """A simple gear silhouette, matching the machining theme of the site."""
    import math

    cx, cy = centre
    for index in range(teeth):
        angle = (360 / teeth) * index
        radians = math.radians(angle)
        tooth_width = math.radians(360 / teeth * 0.34)
        outer = radius * 1.28
        points = []
        for offset in (-tooth_width, tooth_width):
            points.append((
                cx + radius * 0.96 * math.cos(radians + offset),
                cy + radius * 0.96 * math.sin(radians + offset),
            ))
        for offset in (tooth_width * 0.62, -tooth_width * 0.62):
            points.append((
                cx + outer * math.cos(radians + offset),
                cy + outer * math.sin(radians + offset),
            ))
        draw.polygon(points, fill=colour)
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius], fill=colour
    )


def build_icon(size, maskable=False):
    image = Image.new('RGBA', (size, size), BRAND + (255,))
    draw = ImageDraw.Draw(image)

    if not maskable:
        # Rounded corners for the standard icon; the maskable one is squared
        # off because the platform applies its own mask.
        corner = int(size * 0.22)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, size - 1, size - 1], radius=corner, fill=255
        )
        image.putalpha(mask)
        draw = ImageDraw.Draw(image)

    # Content is inset further on the maskable variant so nothing important
    # sits in the region a launcher may crop away.
    inset = 0.30 if maskable else 0.24
    gear_radius = size * inset * 0.62
    _draw_gear(draw, (size / 2, size * 0.36), gear_radius, BRAND_DARK + (110,))

    label = 'SGE'
    font = _load_font(int(size * (0.26 if maskable else 0.30)))
    left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
    draw.text(
        ((size - (right - left)) / 2 - left, size * 0.52 - top),
        label, font=font, fill=WHITE,
    )
    return image


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for size in (192, 512):
        path = OUTPUT_DIR / f'icon-{size}x{size}.png'
        build_icon(size).save(path, 'PNG', optimize=True)
        written.append(path)

        maskable_path = OUTPUT_DIR / f'icon-maskable-{size}x{size}.png'
        build_icon(size, maskable=True).save(maskable_path, 'PNG', optimize=True)
        written.append(maskable_path)

    favicon_path = OUTPUT_DIR / 'favicon.png'
    build_icon(192).resize((64, 64), Image.LANCZOS).save(favicon_path, 'PNG', optimize=True)
    written.append(favicon_path)

    for path in written:
        print(f'{path.relative_to(OUTPUT_DIR.parent.parent)}  '
              f'{path.stat().st_size / 1024:.1f} KB')


if __name__ == '__main__':
    main()
