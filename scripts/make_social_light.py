"""Light-theme explainer graphic with the real InsightTrack, Kaggle and DEV logos.

    python scripts/make_social_light.py

Writes post/social/explainer-light.png (1080x1350, LinkedIn portrait).
Palette: brand colours only. InsightTrack indigo, Kaggle blue, DEV black, a muted
amber for the cheaper models. Slate text on an off-white page, white cards with
soft shadows. Logos live in assets/logos (see its README for sources).
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGOS = os.path.join(ROOT, "assets", "logos")
OUT = os.path.join(ROOT, "post", "social")
FONT = "/System/Library/Fonts/Avenir Next.ttc"
BOLD, DEMI, MEDIUM, REGULAR = 0, 2, 5, 7
S = 2  # supersampling

PAGE = (248, 250, 252)          # slate-50
CARD = (255, 255, 255)
BORDER = (226, 232, 240)        # slate-200
INK = (15, 23, 42)              # slate-900
INK2 = (71, 85, 105)            # slate-600
INK3 = (148, 163, 184)          # slate-400
INDIGO, INDIGO_50 = (79, 70, 229), (238, 242, 255)
KAGGLE = (32, 190, 255)
DEVBLACK = (10, 10, 10)
AMBER, AMBER_50 = (217, 119, 6), (255, 247, 237)
TRACK = (241, 245, 249)         # slate-100

LEADERBOARD = [("Claude Sonnet 5", 100.0), ("GPT-5.5", 99.2), ("Grok 4.20 (reasoning)", 97.9),
               ("Gemini 3.7 Flash", 97.7), ("Gemini 3.5 Flash-Lite", 81.0), ("Claude Haiku 4.5", 77.9),
               ("Grok 4.20 (no reasoning)", 77.1), ("GPT-5.4 nano", 67.1)]


def f(weight, size):
    return ImageFont.truetype(FONT, int(size * S), index=weight)


def logo(name, height):
    img = Image.open(os.path.join(LOGOS, name)).convert("RGBA")
    img = img.crop(img.getbbox())  # trim transparent padding
    w = round(img.width * height / img.height)
    return img.resize((w * S, height * S), Image.LANCZOS)


class Page:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * S, h * S), PAGE + (255,))
        self.d = ImageDraw.Draw(self.img)

    def text(self, xy, s, font, fill=INK, anchor="la"):
        self.d.text((xy[0] * S, xy[1] * S), s, font=font, fill=fill, anchor=anchor)

    def width(self, s, font):
        return self.d.textlength(s, font=font) / S

    def wrap(self, xy, s, font, fill=INK2, max_w=800, line_h=None):
        x, y = xy
        line_h = line_h or font.size / S * 1.35
        line = ""
        for word in s.split():
            test = (line + " " + word).strip()
            if self.width(test, font) <= max_w or not line:
                line = test
            else:
                self.text((x, y), line, font, fill)
                y += line_h
                line = word
        if line:
            self.text((x, y), line, font, fill)
            y += line_h
        return y

    def rect(self, box, fill, radius=0, outline=None, width=0):
        self.d.rounded_rectangle([v * S for v in box], radius=radius * S, fill=fill,
                                 outline=outline, width=width * S)

    def card(self, box, radius=20):
        """White card with a soft drop shadow and a hairline border."""
        x0, y0, x1, y1 = box
        shadow = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [x0 * S, (y0 + 6) * S, x1 * S, (y1 + 6) * S], radius=radius * S, fill=(15, 23, 42, 22))
        self.img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14 * S)))
        self.d = ImageDraw.Draw(self.img)
        self.rect(box, CARD, radius=radius, outline=BORDER, width=1)

    def paste(self, im, x, y):
        self.img.alpha_composite(im, (int(x * S), int(y * S)))
        self.d = ImageDraw.Draw(self.img)

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        out = self.img.convert("RGB").resize((self.w, self.h), Image.LANCZOS)
        out.save(os.path.join(OUT, name), optimize=True)
        print("wrote", os.path.relpath(os.path.join(OUT, name), ROOT))


def logo_row(p, y):
    """InsightTrack  ×  Kaggle  ×  DEV, centred."""
    it = logo("insighttrack.png", 44)
    kg = logo("kaggle-wordmark.png", 40)
    dv = logo("dev-badge.png", 38)
    name_font = f(BOLD, 28)
    x_font = f(MEDIUM, 26)
    gap = 26
    it_w = it.width / S + 12 + p.width("InsightTrack", name_font)
    total = it_w + gap + p.width("×", x_font) + gap + kg.width / S + gap + p.width("×", x_font) + gap + dv.width / S
    x = (p.w - total) / 2
    p.paste(it, x, y)
    p.text((x + it.width / S + 12, y + 22), "InsightTrack", name_font, INK, anchor="lm")
    x += it_w + gap
    p.text((x, y + 22), "×", x_font, INK3, anchor="lm")
    x += p.width("×", x_font) + gap
    p.paste(kg, x, y + 2)
    x += kg.width / S + gap
    p.text((x, y + 22), "×", x_font, INK3, anchor="lm")
    x += p.width("×", x_font) + gap
    p.paste(dv, x, y + 3)


def step(p, n, y, height, color, title, body, rail_x):
    """Timeline step: numbered dot on the rail, content card to the right."""
    r = 22
    p.d.ellipse([(rail_x - r) * S, (y + 26 - r) * S, (rail_x + r) * S, (y + 26 + r) * S], fill=color)
    p.text((rail_x, y + 26), str(n), f(BOLD, 22), (255, 255, 255), anchor="mm")
    x0 = rail_x + 44
    p.card((x0, y, p.w - 64, y + height))
    p.text((x0 + 28, y + 22), title, f(BOLD, 30), INK)
    if body:
        p.wrap((x0 + 28, y + 66), body, f(MEDIUM, 23), INK2, max_w=p.w - 64 - x0 - 56, line_h=32)
    return x0


def explainer_light():
    p = Page(1080, 1350)
    logo_row(p, 64)
    p.text((540, 150), "HACKATHON PROJECT  ·  DEV × KAGGLE BENCHMARKING CHALLENGE", f(DEMI, 17), INK3, anchor="mm")
    # Manual break: an even two-line title instead of an orphaned "real job".
    p.text((64, 180), "How I tested 8 AI models", f(BOLD, 46), INK)
    p.text((64, 236), "on my product's real job", f(BOLD, 46), INK)

    rail_x = 88
    y, gap, h12 = 330, 18, 140
    p.d.line([(rail_x * S, (y + 26) * S), (rail_x * S, (y + 2 * (h12 + gap) + 380 + gap + 26) * S)],
             fill=BORDER, width=3 * S)

    step(p, 1, y, h12, INDIGO, "InsightTrack",
         "Open-source web analytics. Its AI analyst, Pulse, explains why a page's traffic changed.", rail_x)
    y += h12 + gap
    step(p, 2, y, h12, INDIGO, "The benchmark",
         "480 questions from Pulse's real job, checked by the product's own code. No AI grades AI.", rail_x)
    y += h12 + gap

    # Step 3: Kaggle, with all 8 models.
    h3 = 380
    x0 = step(p, 3, y, h3, KAGGLE, "Kaggle runs 8 models", None, rail_x)
    p.text((x0 + 28, y + 66), "Same 480 questions for each. Overall accuracy:", f(MEDIUM, 23), INK2)
    col_gap = 28
    col_w = (p.w - 64 - x0 - 56 - col_gap) / 2
    for i, (name, v) in enumerate(LEADERBOARD):
        cx = x0 + 28 + (i % 2) * (col_w + col_gap)
        cy = y + 116 + (i // 2) * 64
        top_tier = v >= 90
        color = INDIGO if top_tier else AMBER
        p.text((cx, cy), name, f(DEMI, 21), INK)
        p.text((cx + col_w, cy), f"{v:.1f}", f(BOLD, 22), color, anchor="ra")
        p.rect((cx, cy + 36, cx + col_w, cy + 44), TRACK, radius=4)
        p.rect((cx, cy + 36, cx + col_w * v / 100, cy + 44), color, radius=4)
    y += h3 + gap

    step(p, 4, y, 176, DEVBLACK, "The findings, written up on DEV", None, rail_x)
    fx = x0 + 28
    stats = [("100%", "top models on\n\"why did it change?\"", INDIGO),
             ("20–49%", "cheaper models\non the same", AMBER),
             ("100 vs 35", "same model,\nreasoning on vs. off", INK)]
    col = (p.w - 64 - x0 - 56) / 3
    for i, (big, small, color) in enumerate(stats):
        sx = fx + i * col
        p.text((sx, y + 68), big, f(BOLD, 32), color)
        for j, line in enumerate(small.split("\n")):
            p.text((sx, y + 110 + j * 24), line, f(MEDIUM, 19), INK2)

    p.text((64, 1244), "The hard part wasn't calling tools. It was knowing when nothing happened.",
           f(DEMI, 22), INK)
    p.text((64, 1296), "kaggle.com/benchmarks/nishikantaray/insighttrack-analyst-bench", f(MEDIUM, 18), INK3)
    p.text((1016, 1296), "#kagglechallenge", f(BOLD, 19), INDIGO, anchor="ra")
    p.save("explainer-light.png")


def small_logo_row(p, x, y, h=34):
    """Left-aligned  InsightTrack × kaggle × DEV  (for covers)."""
    it = logo("insighttrack.png", h)
    kg = logo("kaggle-wordmark.png", int(h * 0.9))
    dv = logo("dev-badge.png", int(h * 0.86))
    nf, xf = f(BOLD, h * 0.62), f(MEDIUM, h * 0.6)
    mid = y + h / 2
    p.paste(it, x, y)
    x += it.width / S + 10
    p.text((x, mid), "InsightTrack", nf, INK, anchor="lm")
    x += p.width("InsightTrack", nf) + 18
    for im, dy in ((kg, h * 0.05), (dv, h * 0.07)):
        p.text((x, mid), "×", xf, INK3, anchor="lm")
        x += p.width("×", xf) + 18
        p.paste(im, x, y + dy)
        x += im.width / S + 18


def drop_chart(p, box):
    """A page's weekly traffic, flat then a sharp drop, with the AI's verdict."""
    x0, y0, x1, y1 = box
    p.card(box, radius=22)
    pad = 36
    p.text((x0 + pad, y0 + 30), "Weekly pageviews", f(DEMI, 20), INK2)
    cx0, cy0, cx1, cy1 = x0 + pad, y0 + 80, x1 - pad, y1 - 40
    for i in range(4):
        gy = cy0 + (cy1 - cy0) * i / 3
        p.d.line([(cx0 * S, gy * S), (cx1 * S, gy * S)], fill=TRACK, width=2 * S)
    vals = [0.72, 0.70, 0.75, 0.71, 0.74, 0.69, 0.73, 0.38]
    n = len(vals)
    pts = [(cx0 + (cx1 - cx0) * i / (n - 1), cy1 - (cy1 - cy0) * v) for i, v in enumerate(vals)]
    area = [(x * S, y * S) for x, y in pts] + [(cx1 * S, cy1 * S), (cx0 * S, cy1 * S)]
    p.d.polygon(area, fill=INDIGO_50)
    p.d.line([(x * S, y * S) for x, y in pts[:-1]], fill=INDIGO, width=5 * S, joint="curve")
    p.d.line([(x * S, y * S) for x, y in pts[-2:]], fill=AMBER, width=5 * S)
    for x, y in pts[:-1]:
        p.d.ellipse([(x - 6) * S, (y - 6) * S, (x + 6) * S, (y + 6) * S], fill=INDIGO)
    lx, ly = pts[-1]
    p.d.ellipse([(lx - 10) * S, (ly - 10) * S, (lx + 10) * S, (ly + 10) * S], fill=AMBER)
    # Label to the left of the falling segment, clear of the line.
    (px, py) = pts[-2]
    p.text(((px + lx) / 2 - 34, (py + ly) / 2 + 6), "−47%", f(BOLD, 30), AMBER, anchor="rm")
    # The AI's verdict, as a speech bubble.
    bw, bh = 280, 64
    bx1, by0 = cx1, ly + 34
    p.rect((bx1 - bw, by0, bx1, by0 + bh), INK, radius=16)
    p.d.polygon([((bx1 - 40) * S, by0 * S), ((bx1 - 22) * S, (by0 - 14) * S), ((bx1 - 10) * S, by0 * S)], fill=INK)
    p.text((bx1 - bw / 2, by0 + bh / 2), "AI: \"not significant\"", f(DEMI, 22), (255, 255, 255), anchor="mm")


def cover_light(w, h, name):
    """Post / benchmark cover. Title matches the DEV post."""
    p = Page(w, h)
    m = 72
    small_logo_row(p, m, 64 if h < 750 else 80)
    ty = 150 if h < 750 else 190
    p.text((m, ty), "KAGGLE BENCHMARK", f(BOLD, 20), INDIGO)
    lines = ["My Kaggle Benchmark", "Caught AI Models", "Inventing Reasons"]
    for i, line in enumerate(lines):
        p.text((m, ty + 38 + i * 72), line, f(BOLD, 64), INK)
    sy = ty + 38 + len(lines) * 72 + 18
    p.text((m, sy), "8 LLMs · 480 questions · graded by the product's own code", f(MEDIUM, 24), INK2)
    # Three headline results, so the cover alone tells the story.
    stats = [("100%", "top models", INDIGO), ("20–49%", "cheaper models", AMBER), ("35%", "reasoning off", INK)]
    stat_y = sy + (64 if h < 750 else 90)
    x = m
    for big, small, color in stats:
        p.text((x, stat_y), big, f(BOLD, 40), color)
        p.text((x, stat_y + 50), small, f(MEDIUM, 19), INK2)
        x += max(p.width(big, f(BOLD, 40)), p.width(small, f(MEDIUM, 19))) + 56
    p.text((m, stat_y + 82), "on \"why did this page's traffic change?\"", f(MEDIUM, 17), INK3)
    chart_top = 88 if h < 750 else 120
    drop_chart(p, (w * 0.56, chart_top, w - m, h - (70 if h < 750 else 110)))
    p.save(name)


def square_light(size=1200, name="square-light.png"):
    """LinkedIn square (1200x1200): logos, title, drop chart, three results."""
    p = Page(size, size)
    m = 72
    small_logo_row(p, m, 64, h=40)
    p.text((m, 150), "KAGGLE BENCHMARK", f(BOLD, 22), INDIGO)
    for i, line in enumerate(["My Kaggle Benchmark Caught", "AI Models Inventing Reasons"]):
        p.text((m, 188 + i * 70), line, f(BOLD, 60), INK)
    p.text((m, 342), "8 LLMs · 480 questions · graded by the product's own code", f(MEDIUM, 25), INK2)
    drop_chart(p, (m, 410, size - m, 850))
    # Three results as equal cards.
    gap = 24
    cw = (size - 2 * m - 2 * gap) / 3
    stats = [("100%", "top models", INDIGO), ("20–49%", "cheaper models", AMBER), ("35%", "same model,\nreasoning off", INK)]
    for i, (big, small, color) in enumerate(stats):
        x0 = m + i * (cw + gap)
        p.card((x0, 884, x0 + cw, 1044), radius=18)
        p.text((x0 + 28, 910), big, f(BOLD, 44), color)
        for j, line in enumerate(small.split("\n")):
            p.text((x0 + 28, 972 + j * 26), line, f(MEDIUM, 21), INK2)
    p.text((m, 1080), "Accuracy on \"why did this page's traffic change?\"", f(MEDIUM, 20), INK3)
    p.text((m, 1128), "kaggle.com/benchmarks/nishikantaray/insighttrack-analyst-bench", f(MEDIUM, 19), INK3)
    p.text((size - m, 1128), "#kagglechallenge", f(BOLD, 21), INDIGO, anchor="ra")
    p.save(name)


if __name__ == "__main__":
    explainer_light()
    square_light()
    cover_light(1600, 672, "cover-light-dev.png")    # DEV crops covers to 1000:420
    cover_light(1600, 800, "cover-light.png")        # Kaggle benchmark / dataset (2:1)
