"""
Generates Snatchr's brand assets: the icon badge, the .ico app icon,
and the horizontal banner logo used in the app header.
Run once at build time - outputs land in /assets.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os

OUT = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(OUT, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Brand gradient: electric purple -> hot pink -> orange
BRAND_STOPS = [(124, 58, 237), (236, 72, 153), (251, 146, 60)]


def lerp(a, b, t):
    return a + (b - a) * t


def gradient_color(t, stops=BRAND_STOPS):
    """t in [0,1] across a multi-stop gradient."""
    n = len(stops) - 1
    seg = min(int(t * n), n - 1)
    local_t = (t * n) - seg
    c0, c1 = stops[seg], stops[seg + 1]
    return tuple(int(lerp(c0[i], c1[i], local_t)) for i in range(3))


def diagonal_gradient(size, stops=BRAND_STOPS):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    max_d = w + h
    for y in range(h):
        for x in range(w):
            t = (x + y) / max_d
            px[x, y] = gradient_color(t, stops)
    return img


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


def draw_hook_mark(draw, cx, cy, s, color, width_ratio=0.22):
    """Bold 'S' wordmark glyph with a small hook-tail accent (the 'snatch' motif)."""
    font_size = int(s * 1.55)
    font = ImageFont.truetype(FONT_BOLD, font_size)
    bbox = draw.textbbox((0, 0), "S", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw / 2 - bbox[0]
    ty = cy - th / 2 - bbox[1]
    draw.text((tx, ty), "S", font=font, fill=color)

    # Hook-tail accent curling off the bottom of the S, like a claw snagging something
    w = s * width_ratio * 0.55
    hook_cx = cx + s * 0.30
    hook_cy = cy + s * 0.52
    r = s * 0.24
    draw.arc([hook_cx - r, hook_cy - r, hook_cx + r, hook_cy + r],
              start=40, end=280, fill=color, width=int(w))
    tip_r = w * 0.6
    tip_x = hook_cx + r * math.cos(math.radians(40))
    tip_y = hook_cy + r * math.sin(math.radians(40))
    draw.ellipse([tip_x - tip_r, tip_y - tip_r, tip_x + tip_r, tip_y + tip_r], fill=color)


def make_icon_badge(size=512):
    grad = diagonal_gradient((size, size))
    mask = rounded_mask((size, size), radius=int(size * 0.26))

    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    badge.paste(grad, (0, 0), mask)

    # subtle inner glow / vignette for depth
    glow = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([size*0.05, size*0.05, size*0.95, size*0.95], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.12))
    white_layer = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    white_layer.putalpha(glow.point(lambda p: int(p * 0.35)))
    badge = Image.alpha_composite(badge, white_layer)

    draw = ImageDraw.Draw(badge)
    draw_hook_mark(draw, size / 2, size / 2, size * 0.62, (255, 255, 255, 255))

    # thin outer rim highlight
    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    rd.rounded_rectangle([2, 2, size - 3, size - 3], radius=int(size * 0.26),
                          outline=(255, 255, 255, 60), width=max(2, size // 170))
    badge = Image.alpha_composite(badge, rim)

    badge.save(os.path.join(OUT, "logo_icon.png"))
    return badge


def make_ico(badge):
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [badge.resize((s, s), Image.LANCZOS) for s in sizes]
    imgs[0].save(os.path.join(OUT, "icon.ico"), format="ICO",
                 sizes=[(s, s) for s in sizes], append_images=imgs[1:])


def make_banner(icon_badge, w=760, h=200):
    banner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    icon_size = int(h * 0.82)
    icon = icon_badge.resize((icon_size, icon_size), Image.LANCZOS)
    banner.paste(icon, (int(h * 0.09), (h - icon_size) // 2), icon)

    draw = ImageDraw.Draw(banner)
    text_x = int(h * 0.09) + icon_size + int(h * 0.18)

    title_font = ImageFont.truetype(FONT_BOLD, int(h * 0.42))
    tag_font = ImageFont.truetype(FONT_BOLD, int(h * 0.13))

    word = "SNATCHR"
    # per-letter gradient fill for the wordmark
    x_cursor = text_x
    bbox_full = draw.textbbox((0, 0), word, font=title_font)
    total_w = bbox_full[2] - bbox_full[0]
    y_text = int(h * 0.14)

    for i, ch in enumerate(word):
        t = i / max(1, len(word) - 1)
        color = gradient_color(t)
        draw.text((x_cursor, y_text), ch, font=title_font, fill=color)
        cw = draw.textbbox((0, 0), ch, font=title_font)[2]
        x_cursor += cw

    draw.text((text_x + 2, y_text + int(h * 0.46)), "grab it. don't ask.",
              font=tag_font, fill=(180, 180, 195, 255))

    banner.save(os.path.join(OUT, "logo_banner.png"))


if __name__ == "__main__":
    badge = make_icon_badge(512)
    make_ico(badge)
    make_banner(badge)
    print("Assets generated in", OUT)
