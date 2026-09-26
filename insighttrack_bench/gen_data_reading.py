"""Group 2 — reading InsightTrack tool output correctly.

The tool results use the exact field names InsightTrack's queries return
(queries.js: getTrafficSources, getDeviceBreakdown, getTopPages, getKPISummary),
wrapped in the {summary, data} envelope Pulse sees. Every answer is computed
here from the same data the model is shown.

About a quarter of the questions ask for something the result does not contain;
the right answer is "not_available". Those cases measure fabrication.
"""
from __future__ import annotations

import random

DATE_RANGES = ["7d", "30d", "90d"]
SOURCES = ["Search", "Direct", "Social", "Referral", "Email"]
DEVICES = ["desktop", "mobile", "tablet"]
PAGES = ["/", "/pricing", "/signup", "/docs/getting-started", "/blog/acid-properties-explained",
         "/blog/api-rate-limiting", "/blog/sql-joins-visual-guide", "/blog/gdpr-for-developers",
         "/changelog", "/about", "/contact", "/blog/core-web-vitals"]


def _pct_rows(names, counts, key):
    total = sum(counts)
    rows = [{key: n, "visitors": c, "percentage": round(c / total * 100) if total else 0}
            for n, c in zip(names, counts)]
    return sorted(rows, key=lambda r: -r["visitors"])


def _sources(rng):
    counts = rng.sample(range(40, 3000), len(SOURCES))
    rows = _pct_rows(SOURCES, counts, "source")
    return rows, f"Top source was {rows[0]['source']} with {rows[0]['visitors']:,} visitors."


def _devices(rng):
    counts = rng.sample(range(30, 5000), len(DEVICES))
    rows = _pct_rows(DEVICES, counts, "device")
    return rows, f"Most visitors used {rows[0]['device']} ({rows[0]['percentage']}%)."


def _pages(rng):
    paths = rng.sample(PAGES, 10)
    rows = []
    for p in paths:
        uv = rng.randint(20, 2500)
        rows.append({"path": p, "title": p, "views": uv + rng.randint(0, uv * 2), "uniqueVisitors": uv})
    rows.sort(key=lambda r: -r["views"])
    return rows, f"Top page was {rows[0]['path']} with {rows[0]['views']:,} views."


def _kpi(rng):
    visitors = rng.randint(800, 60000)
    sessions = round(visitors * rng.uniform(1.1, 1.6))
    pageviews = round(sessions * rng.uniform(1.4, 3.5))
    trend = round(rng.uniform(-40, 60), 1)
    data = {
        "totalVisitors": visitors, "totalPageviews": pageviews, "totalSessions": sessions,
        "bounceRate": round(rng.uniform(25, 75), 1), "avgSessionDuration": f"{rng.randint(0, 6)}m {rng.randint(0, 59)}s",
        "pagesPerSession": f"{pageviews / sessions:.2f}",
        "visitorsTrend": trend, "pageviewsTrend": round(rng.uniform(-40, 60), 1),
        "bounceRateTrend": round(rng.uniform(-10, 10), 1), "sessionTrend": round(rng.uniform(-40, 60), 1),
    }
    return data, f"{visitors:,} visitors, {pageviews:,} pageviews, {data['bounceRate']}% bounce."


def _by(rows, key, name):
    return next(r for r in rows if r[key] == name)


# Each question: (tool, data_fn, make(rng, data) -> (question, answer, type, tolerance) or None)
def q_source_gap(rng, rows):
    a, b = rng.sample(SOURCES, 2)
    diff = _by(rows, "source", a)["visitors"] - _by(rows, "source", b)["visitors"]
    return f"How many more visitors came from {a} than from {b}? (Negative if fewer.)", diff, "number", 0


def q_source_share(rng, rows):
    a, b = rng.sample(SOURCES, 2)
    total = sum(r["visitors"] for r in rows)
    share = (_by(rows, "source", a)["visitors"] + _by(rows, "source", b)["visitors"]) / total * 100
    return f"What percentage of visitors came from {a} or {b} combined? Round to 1 decimal place.", round(share, 1), "number", 1.0


def q_source_na(rng, rows):
    s = rng.choice(SOURCES)
    return f"What was the bounce rate of visitors from {s}?", "not_available", "unavailable", 0


def q_device_sum(rng, rows):
    total = sum(r["visitors"] for r in rows if r["device"] in ("mobile", "tablet"))
    return "How many visitors used a mobile phone or a tablet?", total, "number", 0


def q_device_ratio(rng, rows):
    ratio = _by(rows, "device", "desktop")["visitors"] / _by(rows, "device", "mobile")["visitors"]
    return "How many desktop visitors were there per mobile visitor? Round to 2 decimal places.", round(ratio, 2), "number", 0.01


def q_device_na(rng, rows):
    d = rng.choice(DEVICES)
    return f"What was the average session duration on {d}?", "not_available", "unavailable", 0


def q_pages_ratio(rng, rows):
    best = max(rows, key=lambda r: r["views"] / r["uniqueVisitors"])
    ratios = sorted((r["views"] / r["uniqueVisitors"] for r in rows), reverse=True)
    if ratios[0] - ratios[1] < 0.05:
        return None  # too close to call — skip rather than ship an ambiguous case
    return "Which page had the most views per unique visitor? Answer with its path.", best["path"], "text", 0


def q_pages_top3(rng, rows):
    return "How many views did the top 3 pages get in total?", sum(r["views"] for r in rows[:3]), "number", 0


def q_pages_blog(rng, rows):
    blog = [r for r in rows if r["path"].startswith("/blog/")]
    if len(blog) < 2 or blog[0]["views"] == blog[1]["views"]:
        return None
    return "Among pages under /blog/, which had the most views? Answer with its path.", blog[0]["path"], "text", 0


def q_pages_na(rng, rows):
    p = rng.choice(rows)["path"]
    return f"What was the bounce rate of {p}?", "not_available", "unavailable", 0


def q_kpi_prev(rng, data):
    prev = data["totalVisitors"] / (1 + data["visitorsTrend"] / 100)
    tol = max(1.0, round(prev * 0.002, 1))  # trend is rounded to 0.1%, so allow that much
    return ("The visitors trend compares this period with the previous one of the same length. "
            "How many visitors did the previous period have? Round to the nearest whole number."), round(prev), "number", tol


def q_kpi_pv_per_visitor(rng, data):
    v = data["totalPageviews"] / data["totalVisitors"]
    return "How many pageviews were there per visitor? Round to 2 decimal places.", round(v, 2), "number", 0.01


def q_kpi_na(rng, data):
    return "How many of these visitors came from India?", "not_available", "unavailable", 0


SPECS = [
    ("get_sources", _sources, [q_source_gap, q_source_share, q_source_na]),
    ("get_devices", _devices, [q_device_sum, q_device_ratio, q_device_na]),
    ("get_top_pages", _pages, [q_pages_ratio, q_pages_top3, q_pages_blog, q_pages_na]),
    ("get_kpi", _kpi, [q_kpi_prev, q_kpi_pv_per_visitor, q_kpi_na]),
]
TOTAL = 80

# ── HARD tier ────────────────────────────────────────────────────────────────
# Rounded fields that give the wrong answer if used, unit conversion, two-step
# arithmetic from trends, and questions that LOOK answerable but are not
# (unique visitors cannot be summed across pages; a top-10 list is not the site).

def h_duration_seconds(rng, data):
    m, sec = (int(x[:-1]) for x in data["avgSessionDuration"].split())
    return "What was the average session duration, in seconds?", m * 60 + sec, "number", 0


def h_prev_pages_per_visitor(rng, data):
    prev_pv = data["totalPageviews"] / (1 + data["pageviewsTrend"] / 100)
    prev_v = data["totalVisitors"] / (1 + data["visitorsTrend"] / 100)
    return ("Both trends compare this period with the previous one of the same length. How many pageviews "
            "per visitor were there in the PREVIOUS period? Round to 2 decimal places."), round(prev_pv / prev_v, 2), "number", 0.02


def h_growth_compare(rng, data):
    if abs(data["pageviewsTrend"] - data["visitorsTrend"]) < 1:
        return None
    ans = "yes" if data["pageviewsTrend"] > data["visitorsTrend"] else "no"
    return "Did pageviews grow faster than visitors compared with the previous period? Answer yes or no.", ans, "text", 0


def h_exact_share(rng, rows):
    total = sum(r["visitors"] for r in rows)
    options = [r for r in rows if abs(r["visitors"] / total * 100 - r["percentage"]) >= 0.3]
    if not options:
        return None
    r = rng.choice(options)
    exact = round(r["visitors"] / total * 100, 1)
    # Tolerance 0.1: the rounded `percentage` field is at least 0.3 away, so it fails.
    return (f"What exact share of visitors came from {r['source']}? Compute it from the visitor counts and round "
            "to 1 decimal place."), exact, "number", 0.1


def h_cross_tab(rng, rows):
    return "What share of Search visitors were on a mobile phone?", "not_available", "unavailable", 0


def h_uniques_total(rng, rows):
    return ("How many unique visitors did these pages have in total? Count each person only once."), \
        "not_available", "unavailable", 0


def h_site_total(rng, rows):
    return "How many views did the whole site get, across all of its pages?", "not_available", "unavailable", 0


def h_median_views(rng, rows):
    v = sorted(r["views"] for r in rows)
    median = (v[4] + v[5]) / 2
    return "What is the median number of views among the listed pages? Round to 1 decimal place.", median, "number", 0.5


HARD_SPECS = [
    ("get_kpi", _kpi, [h_duration_seconds, h_prev_pages_per_visitor, h_growth_compare]),
    ("get_sources", _sources, [h_exact_share, h_cross_tab]),
    ("get_top_pages", _pages, [h_uniques_total, h_site_total, h_median_views]),
]
HARD_TOTAL = 40


def _append(cases, rng, tool, data, summary, made, difficulty):
    question, answer, kind, tol = made
    args = {"dateRange": rng.choice(DATE_RANGES)}
    if tool == "get_top_pages":
        args["limit"] = 10
    cases.append({
        "id": f"read_{len(cases) + 1:03d}",
        "group": "data_reading",
        "subgroup": ("unavailable" if kind == "unavailable" else kind) if difficulty == "standard"
        else "hard_" + ("unavailable" if kind == "unavailable" else "compute"),
        "difficulty": difficulty,
        "tool": tool,
        "tool_args": args,
        "tool_output": {"summary": summary, "data": data},
        "question": question,
        "answer": answer,
        "answer_type": kind,
        "tolerance": tol,
    })


def _fill(cases, rng, specs, target, difficulty):
    flat = [(tool, data_fn, q) for tool, data_fn, qs in specs for q in qs]
    i, guard = 0, 0
    while len(cases) < target:
        guard += 1
        if guard > target * 50:
            raise RuntimeError("could not build data-reading cases")
        tool, data_fn, q = flat[i % len(flat)]
        data, summary = data_fn(rng)
        made = q(rng, data)
        if made is None:
            continue
        i += 1
        _append(cases, rng, tool, data, summary, made, difficulty)


def build(seed: int = 13) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []
    _fill(cases, rng, SPECS, TOTAL, "standard")
    _fill(cases, rng, HARD_SPECS, TOTAL + HARD_TOTAL, "hard")
    return cases
