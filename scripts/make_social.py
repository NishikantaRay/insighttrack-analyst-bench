"""Promotional graphics for social media, in the cover's visual style.

    python scripts/make_social.py

Writes post/social/:
  carousel-01..07.png  1080x1350  LinkedIn document / Instagram carousel
  square.png           1080x1080  single-image post
  landscape.png        1200x675   X / LinkedIn link image
  story.png            1080x1920  Instagram / LinkedIn story

All numbers are the final task-v4 results. Drawn at 2x and downscaled.
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "post", "social")
FONT = "/System/Library/Fonts/Avenir Next.ttc"
BOLD, DEMI, MEDIUM, REGULAR, HEAVY = 0, 2, 5, 7, 8

BG_TOP, BG_BOTTOM = (11, 16, 32), (20, 28, 56)
WHITE, MUTED, FAINT = (240, 244, 255), (150, 162, 196), (70, 82, 120)
TEAL, AMBER, ROSE = (45, 212, 191), (251, 191, 36), (251, 113, 133)
PANEL, PANEL_EDGE, TRACK = (17, 24, 48), (44, 56, 98), (32, 42, 78)
S = 2  # supersampling

LEADERBOARD = [("Claude Sonnet 5", 100.0), ("GPT-5.5", 99.2), ("Grok 4.20 (reasoning)", 97.9),
               ("Gemini 3.7 Flash", 97.7), ("Gemini 3.5 Flash-Lite", 81.0), ("Claude Haiku 4.5", 77.9),
               ("Grok 4.20 (no reasoning)", 77.1), ("GPT-5.4 nano", 67.1)]
DIAGNOSIS = [("Claude Sonnet 5", 100), ("Gemini 3.7 Flash", 100), ("Grok (reasoning)", 100),
             ("GPT-5.5", 96.7), ("Gemini Flash-Lite", 49.2), ("Claude Haiku 4.5", 44.2),
             ("Grok (no reasoning)", 35.0), ("GPT-5.4 nano", 20.0)]


def f(weight, size):
    return ImageFont.truetype(FONT, int(size * S), index=weight)


class Canvas:
    def __init__(self, w, h, glow=True):
        self.w, self.h = w, h
        W, H = w * S, h * S
        img = Image.new("RGB", (W, H))
        px = img.load()
        for y in range(H):
            t = y / (H - 1)
            c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
            for x in range(W):
                px[x, y] = c
        if glow:
            g = Image.new("RGB", (W, H), (0, 0, 0))
            ImageDraw.Draw(g).ellipse([int(W * 0.45), -int(H * 0.25), int(W * 1.25), int(H * 0.45)], fill=(20, 70, 90))
            img = Image.blend(img, g.filter(ImageFilter.GaussianBlur(120 * S)), 0.35)
        self.img = img
        self.d = ImageDraw.Draw(img)

    # ── primitives (all coordinates in output pixels) ──
    def text(self, xy, s, font, fill=WHITE, anchor="la"):
        self.d.text((xy[0] * S, xy[1] * S), s, font=font, fill=fill, anchor=anchor)

    def width(self, s, font):
        return self.d.textlength(s, font=font) / S

    def wrap(self, xy, s, font, fill=WHITE, max_w=900, line_h=None):
        """Word-wrap to max_w; returns the y below the last line."""
        x, y = xy
        size = font.size / S
        line_h = line_h or size * 1.28
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
        b = [v * S for v in box]
        self.d.rounded_rectangle(b, radius=radius * S, fill=fill, outline=outline, width=width * S)

    def pill(self, x, y, label, fill=TRACK, color=WHITE, size=22):
        font = f(DEMI, size)
        tw = self.width(label, font)
        h = size * 2.1
        self.rect((x, y, x + tw + size * 1.6, y + h), fill, radius=int(h / 2), outline=(58, 72, 120), width=1)
        self.text((x + size * 0.8, y + h / 2), label, font, color, anchor="lm")
        return x + tw + size * 1.6 + 12

    def arrow(self, x, y, length=46, color=TEAL, thick=5):
        """A right arrow drawn as shapes (Avenir has no arrow glyph)."""
        d, k = self.d, S
        d.line([(x * k, y * k), ((x + length) * k, y * k)], fill=color, width=thick * k)
        d.polygon([((x + length + 4) * k, y * k), ((x + length - 14) * k, (y - 13) * k),
                   ((x + length - 14) * k, (y + 13) * k)], fill=color)

    def brand(self, x, y, size=22):
        self.text((x, y), "INSIGHTTRACK ANALYST BENCH", f(BOLD, size), TEAL)

    def footer(self, left, y, page=None, total=None):
        self.text((left, y), "kaggle.com/benchmarks/nishikantaray/insighttrack-analyst-bench", f(MEDIUM, 20), FAINT)
        if page:
            self.text((self.w - left, y), f"{page} / {total}", f(DEMI, 20), MUTED, anchor="ra")

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        self.img.resize((self.w, self.h), Image.LANCZOS).save(os.path.join(OUT, name), optimize=True)
        print("wrote", os.path.relpath(os.path.join(OUT, name), ROOT))


def bars(c, x, y, w, rows, bar_h=34, gap=18, label_w=300, highlight_below=None, size=24):
    """Horizontal bars with the value at the end. Cheap models (< highlight_below) in rose."""
    for i, (name, v) in enumerate(rows):
        yy = y + i * (bar_h + gap)
        c.text((x, yy + bar_h / 2), name, f(MEDIUM, size), WHITE, anchor="lm")
        bx = x + label_w
        bw = w - label_w - 120
        c.rect((bx, yy, bx + bw, yy + bar_h), TRACK, radius=8)
        color = ROSE if highlight_below is not None and v < highlight_below else TEAL
        c.rect((bx, yy, bx + max(bw * v / 100, 12), yy + bar_h), color, radius=8)
        label = "100%" if v >= 100 else f"{v:.1f}%"
        c.text((bx + bw + 16, yy + bar_h / 2), label, f(BOLD, size), WHITE, anchor="lm")
    return y + len(rows) * (bar_h + gap)


# ── carousel (1080x1350) ─────────────────────────────────────────────────────
W, H, M = 1080, 1350, 84
TOTAL = 7


def slide_hook():
    c = Canvas(W, H)
    c.brand(M, 110)
    y = c.wrap((M, 170), "I gave 8 AI models my product's real job.", f(HEAVY, 88), WHITE, max_w=W - 2 * M, line_h=102)
    y = c.wrap((M, y + 30), "The cheap ones either invent a reason, or shrug.", f(BOLD, 52), ROSE, max_w=W - 2 * M, line_h=66)
    c.wrap((M, y + 50), "480 questions. Graded by the product's own code, not by another AI.", f(MEDIUM, 34), MUTED, max_w=W - 2 * M, line_h=46)
    x = M
    for label in ("Tool choice", "Data reading", "Diagnosis", "SQL"):
        x = c.pill(x, 880, label, size=24)
    c.text((M, 1020), "8 models  ·  480 cases  ·  0 AI judges", f(BOLD, 32), AMBER)
    c.text((M, 1190), "Swipe for the results", f(BOLD, 34), TEAL)
    c.arrow(M + c.width("Swipe for the results", f(BOLD, 34)) + 24, 1212)
    c.footer(M, 1275, 1, TOTAL)
    c.save("carousel-01.png")


def slide_setup():
    c = Canvas(W, H)
    c.brand(M, 110)
    c.wrap((M, 160), "The job: be Pulse, InsightTrack's AI analyst", f(HEAVY, 64), WHITE, max_w=W - 2 * M, line_h=76)
    steps = [
        ("1", "Pick the right tool", "from 23 real ones, or say \"none\""),
        ("2", "Read the data", "and say \"not available\" instead of guessing"),
        ("3", "Explain why traffic changed", "real change or noise, and the exact cause"),
        ("4", "Write the SQL", "run it, and check the result"),
    ]
    y = 420
    for num, head, sub in steps:
        c.rect((M, y, W - M, y + 150), PANEL, radius=22, outline=PANEL_EDGE, width=2)
        c.rect((M + 28, y + 35, M + 108, y + 115), TEAL, radius=40)
        c.text((M + 68, y + 75), num, f(HEAVY, 42), (8, 30, 30), anchor="mm")
        c.text((M + 140, y + 42), head, f(BOLD, 38), WHITE)
        c.text((M + 140, y + 94), sub, f(MEDIUM, 28), MUTED)
        y += 180
    c.text((M, 1165), "8 models  ·  480 cases  ·  0 AI judges", f(BOLD, 34), AMBER)
    c.footer(M, 1275, 2, TOTAL)
    c.save("carousel-02.png")


def slide_split():
    c = Canvas(W, H)
    c.brand(M, 110)
    c.wrap((M, 160), "Tool calling is solved. Explaining \"why\" is not.", f(HEAVY, 62), WHITE, max_w=W - 2 * M, line_h=74)
    c.text((M, 360), "Diagnosis: why did this page's traffic change?", f(DEMI, 30), MUTED)
    bars(c, M, 430, W - 2 * M, DIAGNOSIS, bar_h=46, gap=28, label_w=330, highlight_below=90, size=28)
    c.rect((M, 1080, W - M, 1200), PANEL, radius=22, outline=PANEL_EDGE, width=2)
    c.text((M + 36, 1140), "Every model picked the right tool 93–100% of the time.", f(DEMI, 30), WHITE, anchor="lm")
    c.footer(M, 1275, 3, TOTAL)
    c.save("carousel-03.png")


def slide_reasoning():
    c = Canvas(W, H)
    c.brand(M, 110)
    c.text((M, 160), "Same model. One switch.", f(HEAVY, 64), WHITE)
    c.text((M, 270), "Grok 4.20 on diagnosis", f(DEMI, 34), MUTED)
    col_w = (W - 2 * M - 40) / 2
    for i, (label, val, color) in enumerate((("Reasoning ON", "100%", TEAL), ("Reasoning OFF", "35%", ROSE))):
        x0 = M + i * (col_w + 40)
        c.rect((x0, 380, x0 + col_w, 860), PANEL, radius=28, outline=PANEL_EDGE, width=2)
        c.text((x0 + col_w / 2, 450), label, f(BOLD, 34), MUTED, anchor="mm")
        c.text((x0 + col_w / 2, 640), val, f(HEAVY, 118), color, anchor="mm")
    c.wrap((M, 930), "It lost all 16 multi-cause cases and 9 of 12 decoys without reasoning.", f(MEDIUM, 34), WHITE, max_w=W - 2 * M, line_h=46)
    c.wrap((M, 1060), "If your AI answers \"why\" questions, reasoning isn't optional.", f(BOLD, 36), AMBER, max_w=W - 2 * M, line_h=48)
    c.footer(M, 1275, 4, TOTAL)
    c.save("carousel-04.png")


def slide_failures():
    c = Canvas(W, H)
    c.brand(M, 110)
    c.wrap((M, 160), "Two ways to be wrong", f(HEAVY, 72), WHITE, max_w=W - 2 * M, line_h=84)
    cards = [
        ("THE ALARMIST", "Grok 4.20 (no reasoning)", "34", "times it invented a search cause that wasn't there",
         "Traffic rose from 437 to 538. It blamed a rank drop.", AMBER),
        ("THE SHRUGGER", "GPT-5.4 nano", "73", "times it called a real change \"noise\"",
         "Traffic fell 47%. It said: not significant.", ROSE),
    ]
    y = 320
    for tag, who, big, what, example, color in cards:
        c.rect((M, y, W - M, y + 400), PANEL, radius=28, outline=PANEL_EDGE, width=2)
        c.rect((M, y, M + 12, y + 400), color, radius=6)
        c.text((M + 50, y + 44), tag, f(HEAVY, 30), color)
        c.text((M + 50, y + 90), who, f(DEMI, 28), MUTED)
        c.text((M + 50, y + 150), big, f(HEAVY, 110), WHITE)
        c.wrap((M + 250, y + 170), what, f(DEMI, 32), WHITE, max_w=W - 2 * M - 300, line_h=42)
        c.wrap((M + 50, y + 305), example, f(MEDIUM, 28), MUTED, max_w=W - 2 * M - 100, line_h=38)
        y += 440
    c.text((M, 1200), "The shrugger is the dangerous one.", f(BOLD, 34), ROSE)
    c.footer(M, 1275, 5, TOTAL)
    c.save("carousel-05.png")


def slide_leaderboard():
    c = Canvas(W, H)
    c.brand(M, 110)
    c.wrap((M, 160), "The final leaderboard", f(HEAVY, 72), WHITE, max_w=W - 2 * M, line_h=84)
    c.text((M, 290), "Average accuracy across all four tasks", f(DEMI, 30), MUTED)
    bars(c, M, 370, W - 2 * M, LEADERBOARD, bar_h=44, gap=30, label_w=380, highlight_below=90, size=27)
    c.rect((M, 1010, W - M, 1200), PANEL, radius=22, outline=PANEL_EDGE, width=2)
    c.text((M + 36, 1050), "BEST VALUE", f(HEAVY, 26), TEAL)
    c.wrap((M + 36, 1092), "Gemini 3.7 Flash: 97.7% at about half the cost of the top model.", f(DEMI, 32), WHITE, max_w=W - 2 * M - 72, line_h=42)
    c.footer(M, 1275, 6, TOTAL)
    c.save("carousel-06.png")


def slide_lessons():
    c = Canvas(W, H)
    c.brand(M, 110)
    c.wrap((M, 160), "What I'd tell anyone building an AI assistant", f(HEAVY, 60), WHITE, max_w=W - 2 * M, line_h=72)
    lessons = [
        "Compute thresholds in code. Let the model explain.",
        "Test \"nothing happened\" cases, not just causes.",
        "Use reasoning for \"why\" questions.",
        "Check generated SQL against your real database.",
        "A benchmark's prompt is code too.",
    ]
    y = 400
    for i, line in enumerate(lessons, 1):
        c.text((M, y), f"{i:02d}", f(HEAVY, 40), TEAL)
        c.wrap((M + 90, y + 4), line, f(DEMI, 34), WHITE, max_w=W - 2 * M - 90, line_h=44)
        y += 118
    c.rect((M, 1030, W - M, 1200), TEAL, radius=26)
    c.text((W / 2, 1090), "Read the full write-up on DEV", f(HEAVY, 38), (8, 30, 30), anchor="mm")
    c.text((W / 2, 1150), "#kagglechallenge  #devchallenge", f(DEMI, 28), (8, 50, 50), anchor="mm")
    c.footer(M, 1275, 7, TOTAL)
    c.save("carousel-07.png")


# ── single images ────────────────────────────────────────────────────────────

def square():
    c = Canvas(1080, 1080)
    m = 80
    c.brand(m, 90)
    c.wrap((m, 150), "Tool calling is solved. Knowing when nothing happened isn't.", f(HEAVY, 64), WHITE, max_w=1080 - 2 * m, line_h=76)
    c.text((m, 440), "Diagnosis accuracy, 8 models", f(DEMI, 28), MUTED)
    bars(c, m, 500, 1080 - 2 * m, DIAGNOSIS, bar_h=34, gap=20, label_w=300, highlight_below=90, size=24)
    c.text((m, 985), "480 cases · graded by the product's own code", f(DEMI, 26), AMBER)
    c.text((1080 - m, 985), "#kagglechallenge", f(BOLD, 26), TEAL, anchor="ra")
    c.save("square.png")


def landscape():
    c = Canvas(1200, 675)
    m = 64
    c.brand(m, 60, size=20)
    c.wrap((m, 100), "I tested 8 LLMs on my analytics product's real AI job.", f(HEAVY, 50), WHITE, max_w=620, line_h=60)
    c.text((m, 330), "Reasoning on vs. off, same model:", f(DEMI, 26), MUTED)
    big = f(HEAVY, 96)
    x = m
    c.text((x, 370), "100%", big, TEAL)
    x += c.width("100%", big) + 24
    c.text((x, 420), "vs", f(BOLD, 40), MUTED)
    x += c.width("vs", f(BOLD, 40)) + 24
    c.text((x, 370), "35%", big, ROSE)
    c.text((m, 560), "480 cases · 4 tasks · 0 AI judges", f(DEMI, 24), AMBER)
    # Right: mini leaderboard.
    x0 = 740
    c.rect((x0, 70, 1136, 610), PANEL, radius=24, outline=PANEL_EDGE, width=2)
    c.text((x0 + 30, 100), "Leaderboard", f(BOLD, 26), WHITE)
    for i, (name, v) in enumerate(LEADERBOARD):
        y = 160 + i * 54
        color = TEAL if v >= 90 else ROSE
        c.text((x0 + 30, y), name, f(MEDIUM, 21), WHITE)
        c.text((1106, y), f"{v:.1f}", f(BOLD, 22), color, anchor="ra")
    c.save("landscape.png")


def story():
    c = Canvas(1080, 1920)
    m = 90
    c.brand(m, 190, size=26)
    y = c.wrap((m, 260), "I gave 8 AI models my product's real job.", f(HEAVY, 96), WHITE, max_w=1080 - 2 * m, line_h=110)
    c.text((m, y + 60), "The cheapest one saw traffic fall", f(DEMI, 44), MUTED)
    c.text((m, y + 180), "−47%", f(HEAVY, 200), ROSE)
    c.text((m, y + 430), "and said: \"not significant\".", f(DEMI, 44), MUTED)
    c.rect((m, 1300, 1080 - m, 1580), PANEL, radius=30, outline=PANEL_EDGE, width=2)
    c.text((m + 40, 1340), "DIAGNOSIS ACCURACY", f(HEAVY, 26), MUTED)
    c.text((m + 40, 1400), "Top models: 100%", f(HEAVY, 46), TEAL)
    c.text((m + 40, 1480), "Cheaper models: 20–49%", f(HEAVY, 46), ROSE)
    c.rect((m, 1640, 1080 - m, 1770), TEAL, radius=65)
    c.text((540, 1705), "Full results · link in bio", f(HEAVY, 40), (8, 30, 30), anchor="mm")
    c.save("story.png")


def down_arrow(c, x, y, length=34, color=MUTED):
    d, k = c.d, S
    d.line([(x * k, y * k), (x * k, (y + length) * k)], fill=color, width=4 * k)
    d.polygon([(x * k, (y + length + 12) * k), ((x - 11) * k, (y + length - 4) * k),
               ((x + 11) * k, (y + length - 4) * k)], fill=color)


def node(c, box, step, title, sub, accent):
    x0, y0, x1, y1 = box
    c.rect(box, PANEL, radius=24, outline=PANEL_EDGE, width=2)
    c.rect((x0, y0, x0 + 10, y1), accent, radius=5)
    c.rect((x0 + 34, y0 + 30, x0 + 94, y0 + 90), accent, radius=30)
    c.text((x0 + 64, y0 + 60), step, f(HEAVY, 30), (8, 30, 30), anchor="mm")
    c.text((x0 + 120, y0 + 24), title, f(HEAVY, 34), WHITE)
    c.wrap((x0 + 120, y0 + 72), sub, f(MEDIUM, 24), MUTED, max_w=x1 - x0 - 150, line_h=32)


def explainer():
    """One-image explainer: InsightTrack -> benchmark -> Kaggle (8 models) -> DEV."""
    c = Canvas(1080, 1350)
    m = 70
    x = m
    for label, color in (("InsightTrack", TEAL), ("Kaggle", AMBER), ("DEV", WHITE)):
        x = c.pill(x, 70, label, color=color, size=22)
        if label != "DEV":
            c.text((x - 2, 93), "x", f(BOLD, 24), FAINT, anchor="lm")
            x += 26
    c.text((1080 - m, 93), "Hackathon project", f(DEMI, 22), MUTED, anchor="rm")
    c.wrap((m, 150), "How I tested 8 AI models on my product's real job", f(HEAVY, 52), WHITE, max_w=1080 - 2 * m, line_h=62)

    w0, w1 = m, 1080 - m
    NH, GAP = 148, 50  # node height; gap holding the arrow
    y = 288
    node(c, (w0, y, w1, y + NH), "1", "InsightTrack",
         "My open-source analytics app. Its AI analyst, Pulse, explains why traffic changed.", TEAL)
    down_arrow(c, 540, y + NH + 6, length=24)
    y += NH + GAP
    node(c, (w0, y, w1, y + NH), "2", "The benchmark",
         "480 questions from Pulse's real job. Graded by the product's own code, not by AI.", TEAL)
    down_arrow(c, 540, y + NH + 6, length=24)
    y += NH + GAP

    # Kaggle node: all 8 models with their overall score.
    KH = 300
    c.rect((w0, y, w1, y + KH), PANEL, radius=24, outline=PANEL_EDGE, width=2)
    c.rect((w0, y, w0 + 10, y + KH), AMBER, radius=5)
    c.rect((w0 + 34, y + 30, w0 + 94, y + 90), AMBER, radius=30)
    c.text((w0 + 64, y + 60), "3", f(HEAVY, 30), (8, 30, 30), anchor="mm")
    c.text((w0 + 120, y + 24), "Kaggle runs 8 models", f(HEAVY, 34), WHITE)
    c.text((w0 + 120, y + 72), "Same 480 questions each. Overall score:", f(MEDIUM, 24), MUTED)
    col_w = (w1 - w0 - 80) / 2
    for i, (name, v) in enumerate(LEADERBOARD):
        cx = w0 + 40 + (i % 2) * col_w
        cy = y + 120 + (i // 2) * 42
        color = TEAL if v >= 90 else ROSE
        c.rect((cx, cy, cx + col_w - 16, cy + 34), TRACK, radius=10)
        c.text((cx + 14, cy + 17), name, f(DEMI, 20), WHITE, anchor="lm")
        c.text((cx + col_w - 30, cy + 17), f"{v:.1f}", f(HEAVY, 21), color, anchor="rm")
    down_arrow(c, 540, y + KH + 6, length=24)
    y += KH + GAP

    node(c, (w0, y, w1, y + NH), "4", "The findings, on DEV",
         "Top models: 100% at explaining traffic changes. Cheaper: 20-49%. Reasoning on vs. off: 100% vs. 35%.", ROSE)

    c.text((m, 1222), "Knowing when nothing happened is the hard part.", f(BOLD, 28), AMBER)
    c.text((m, 1282), "kaggle.com/benchmarks/nishikantaray/insighttrack-analyst-bench", f(MEDIUM, 20), FAINT)
    c.text((1080 - m, 1282), "#kagglechallenge", f(BOLD, 22), TEAL, anchor="ra")
    c.save("explainer.png")


def main():
    for fn in (slide_hook, slide_setup, slide_split, slide_reasoning, slide_failures, slide_leaderboard,
               slide_lessons, square, landscape, story, explainer):
        fn()


if __name__ == "__main__":
    main()
