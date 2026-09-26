"""Cover images for the Kaggle benchmark and dataset.

    python scripts/make_cover.py

Writes assets/cover.png (1600x800, 2:1) and assets/banner.png (1600x400).
Drawn at 2x and downscaled for smooth edges. No scores are printed on the
image, so it never goes stale when results change.
"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "/System/Library/Fonts/Avenir Next.ttc"
BOLD, DEMI, MEDIUM, REGULAR = 0, 2, 5, 7

BG_TOP, BG_BOTTOM = (11, 16, 32), (20, 28, 56)
WHITE, MUTED, FAINT = (240, 244, 255), (150, 162, 196), (70, 82, 120)
TEAL, AMBER, ROSE = (45, 212, 191), (251, 191, 36), (251, 113, 133)
CHIP_BG = (32, 42, 78)


def font(weight, size):
    return ImageFont.truetype(FONT, size, index=weight)


def gradient(w, h):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def chip(draw, x, y, text, s):
    f = font(DEMI, int(26 * s))
    tw = draw.textlength(text, font=f)
    pad_x, h = int(22 * s), int(52 * s)
    draw.rounded_rectangle([x, y, x + tw + 2 * pad_x, y + h], radius=h // 2, fill=CHIP_BG,
                           outline=(58, 72, 120), width=max(1, int(2 * s)))
    draw.text((x + pad_x, y + h / 2), text, font=f, fill=WHITE, anchor="lm")
    return x + tw + 2 * pad_x + int(14 * s)


def traffic_panel(draw, box, s, seed=7):
    """A page's weekly traffic that drops at the end — the diagnosis question."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=int(28 * s), fill=(17, 24, 48), outline=(44, 56, 98), width=int(2 * s))
    pad = int(40 * s)
    cx0, cy0, cx1, cy1 = x0 + pad, y0 + int(90 * s), x1 - pad, y1 - int(70 * s)
    draw.text((x0 + pad, y0 + int(34 * s)), "Weekly pageviews", font=font(DEMI, int(26 * s)), fill=MUTED)
    for i in range(4):  # gridlines
        gy = cy0 + (cy1 - cy0) * i / 3
        draw.line([(cx0, gy), (cx1, gy)], fill=(32, 42, 74), width=max(1, int(2 * s)))

    rng = random.Random(seed)
    values = [0.62 + rng.uniform(-0.05, 0.05) for _ in range(9)] + [0.30]
    n = len(values)
    pts = [(cx0 + (cx1 - cx0) * i / (n - 1), cy1 - (cy1 - cy0) * v) for i, v in enumerate(values)]
    area = pts + [(cx1, cy1), (cx0, cy1)]
    draw.polygon(area, fill=(24, 60, 78))
    draw.line(pts[:-1], fill=TEAL, width=int(6 * s), joint="curve")
    draw.line(pts[-2:], fill=ROSE, width=int(6 * s))
    for p in pts[:-1]:
        r = int(7 * s)
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=TEAL)
    px, py = pts[-1]
    r = int(13 * s)
    draw.ellipse([px - r, py - r, px + r, py + r], fill=ROSE)

    # The question the benchmark asks.
    q = "Real drop, or noise?"
    f = font(BOLD, int(30 * s))
    tw = draw.textlength(q, font=f)
    bx1, by0 = cx1, py + int(34 * s)
    draw.rounded_rectangle([bx1 - tw - int(36 * s), by0, bx1, by0 + int(58 * s)], radius=int(14 * s), fill=ROSE)
    draw.text((bx1 - tw / 2 - int(18 * s), by0 + int(29 * s)), q, font=f, fill=(40, 10, 20), anchor="mm")
    draw.text((x0 + pad, y1 - int(48 * s)), "Search rank #3 to #6   ·   AI answer now quotes rivals",
              font=font(MEDIUM, int(22 * s)), fill=MUTED)


def cover(w=1600, h=800, scale=2):
    s = scale
    W, H = w * s, h * s
    img = gradient(W, H)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([int(W * 0.55), -int(H * 0.3), int(W * 1.15), int(H * 0.7)], fill=(20, 70, 90))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(160 * s)), 0.35)
    d = ImageDraw.Draw(img)

    left = int(90 * s)
    d.text((left, int(110 * s)), "KAGGLE BENCHMARK", font=font(BOLD, int(26 * s)), fill=TEAL)
    d.text((left, int(150 * s)), "InsightTrack", font=font(BOLD, int(96 * s)), fill=WHITE)
    d.text((left, int(250 * s)), "Analyst Bench", font=font(BOLD, int(96 * s)), fill=WHITE)
    d.text((left, int(380 * s)), "Which LLM should run the AI analyst", font=font(MEDIUM, int(36 * s)), fill=MUTED)
    d.text((left, int(426 * s)), "inside a real analytics product?", font=font(MEDIUM, int(36 * s)), fill=MUTED)

    x = left
    for label in ("Tool choice", "Data reading", "Diagnosis", "SQL"):
        x = chip(d, x, int(510 * s), label, s)

    d.line([(left, int(620 * s)), (int(905 * s), int(620 * s))], fill=FAINT, width=int(2 * s))
    # Column x-offsets sized to each label, so nothing overlaps.
    stats = [(0, "480", "auto-graded cases"), (230, "80 + 40", "standard + hard per task"),
             (540, "0", "LLM judges: all rule-graded")]
    for dx, big, small in stats:
        sx = left + int(dx * s)
        d.text((sx, int(650 * s)), big, font=font(BOLD, int(44 * s)), fill=AMBER)
        d.text((sx, int(708 * s)), small, font=font(MEDIUM, int(22 * s)), fill=MUTED)

    traffic_panel(d, (int(930 * s), int(150 * s), int(1520 * s), int(650 * s)), s)
    d.text((int(1520 * s), int(708 * s)), "github.com/NishikantaRay/InsightTrack",
           font=font(MEDIUM, int(22 * s)), fill=FAINT, anchor="ra")
    return img.resize((w, h), Image.LANCZOS)


def banner(w=1600, h=400, scale=2):
    s = scale
    W, H = w * s, h * s
    img = gradient(W, H)
    d = ImageDraw.Draw(img)
    left = int(80 * s)
    d.text((left, int(70 * s)), "KAGGLE BENCHMARK", font=font(BOLD, int(22 * s)), fill=TEAL)
    d.text((left, int(100 * s)), "InsightTrack Analyst Bench", font=font(BOLD, int(76 * s)), fill=WHITE)
    d.text((left, int(200 * s)), "480 auto-graded cases from a real product's AI analyst job",
           font=font(MEDIUM, int(30 * s)), fill=MUTED)
    x = left
    for label in ("Tool choice", "Data reading", "Diagnosis", "SQL"):
        x = chip(d, x, int(270 * s), label, s)
    # Small traffic sparkline on the right.
    rng = random.Random(3)
    vals = [0.6 + rng.uniform(-0.06, 0.06) for _ in range(9)] + [0.25]
    x0, x1, y0, y1 = int(1180 * s), int(1520 * s), int(120 * s), int(300 * s)
    pts = [(x0 + (x1 - x0) * i / 9, y1 - (y1 - y0) * v) for i, v in enumerate(vals)]
    d.line(pts[:-1], fill=TEAL, width=int(6 * s), joint="curve")
    d.line(pts[-2:], fill=ROSE, width=int(6 * s))
    r = int(12 * s)
    d.ellipse([pts[-1][0] - r, pts[-1][1] - r, pts[-1][0] + r, pts[-1][1] + r], fill=ROSE)
    return img.resize((w, h), Image.LANCZOS)


def main():
    out = os.path.join(ROOT, "assets")
    os.makedirs(out, exist_ok=True)
    cover().save(os.path.join(out, "cover.png"), optimize=True)
    banner().save(os.path.join(out, "banner.png"), optimize=True)
    print("wrote assets/cover.png (1600x800) and assets/banner.png (1600x400)")


if __name__ == "__main__":
    main()
