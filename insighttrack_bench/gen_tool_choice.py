"""Group 1 — tool choice over InsightTrack's real 23-tool Pulse catalogue.

Each template names the tool(s) that genuinely answer it. Where two tools are
both defensible (a funnel drop-off could be read from the user-flow tool too),
both are accepted — the benchmark punishes wrong choices, not judgement calls.
Only arguments the question states are checked.
"""
from __future__ import annotations

import random

DATE_PHRASES = [
    ("in the last 7 days", "7d"),
    ("over the last 30 days", "30d"),
    ("over the last 90 days", "90d"),
    ("today", "today"),
    ("between 1 and 15 August 2026", "custom:2026-08-01:2026-08-15"),
    ("from 2026-07-01 to 2026-07-31", "custom:2026-07-01:2026-07-31"),
]
PATHS = ["/pricing", "/blog/acid-properties-explained", "/signup", "/docs/getting-started", "/checkout"]
KEYWORDS = ["free email templates", "acid properties explained", "api rate limiting", "sql joins visual guide"]


def _dr(rng):
    return rng.choice(DATE_PHRASES)


# Each template: (make(rng) -> (question, expected_args), expected_tools, subgroup)
def _t(text, tools, subgroup="direct", date=True, extra=None):
    def make(rng):
        args = {}
        fmt = {}
        if date:
            phrase, value = _dr(rng)
            fmt["dr"] = phrase
            args["dateRange"] = value
        if extra:
            for key, (placeholder, pick) in extra.items():
                value = pick(rng)
                fmt[placeholder] = value
                args[key] = value
        return text.format(**fmt), args
    return make, tools, subgroup


LIMITS = lambda rng: rng.choice([3, 5, 10, 20])  # noqa: E731
PATH = lambda rng: rng.choice(PATHS)  # noqa: E731
KW = lambda rng: rng.choice(KEYWORDS)  # noqa: E731

TEMPLATES = [
    _t("How is my site doing {dr}?", ["get_kpi"]),
    _t("Give me visitors, pageviews and bounce rate {dr}.", ["get_kpi"]),
    _t("Show me a chart of visitors over time {dr}.", ["get_traffic"]),
    _t("Plot my daily sessions {dr}.", ["get_traffic"]),
    _t("Which {n} pages got the most views {dr}?", ["get_top_pages"], extra={"limit": ("n", LIMITS)}),
    _t("What is my most popular content {dr}?", ["get_top_pages"]),
    _t("Where does my traffic come from {dr}?", ["get_sources"]),
    _t("How much of my traffic came from social media versus search engines {dr}?", ["get_sources"]),
    _t("What share of my visitors used a mobile phone {dr}?", ["get_devices"]),
    _t("Which {n} countries sent the most visitors {dr}?", ["get_countries"], extra={"limit": ("n", LIMITS)}),
    _t("Where in the world are my visitors from {dr}?", ["get_countries"]),
    _t("Where are users dropping out of my signup funnel {dr}?", ["get_funnel", "get_user_flow"], "near_miss"),
    _t("How many people are on my site right now?", ["get_realtime"], date=False),
    _t("Which pages are being viewed live at this moment?", ["get_realtime"], date=False),
    _t("How are my UTM campaigns performing {dr}?", ["get_acquisition_utm"]),
    _t("Which utm_source brought the most visitors {dr}?", ["get_acquisition_utm"], "near_miss"),
    _t("How far down the page do visitors scroll {dr}?", ["get_engagement"]),
    _t("Were there any rage clicks {dr}?", ["get_engagement"]),
    _t("How does this week's traffic compare to last week's?", ["compare_ranges"], date=False),
    _t("Compare my visitors in this period against the previous period of the same length.", ["compare_ranges"], date=False),
    _t("Which websites do I have access to?", ["list_sites"], date=False),
    _t("List all of my sites and my role on each.", ["list_sites"], date=False),
    _t("How many conversions did my newsletter-signup goal get {dr}?", ["get_goals"], "near_miss"),
    _t("What are the top entry and exit pages {dr}?", ["get_user_flow"]),
    _t("Where do visitors go after landing on the homepage {dr}?", ["get_user_flow"]),
    _t("Are there any JavaScript errors being thrown in the browser {dr}?", ["get_js_errors"], "near_miss"),
    _t("What are my LCP and CLS values {dr}?", ["get_performance"]),
    _t("How fast is my site according to Core Web Vitals {dr}?", ["get_performance"]),
    _t("What do visitors click on {p} {dr}?", ["get_page_detail"], extra={"path": ("p", PATH)}),
    _t("How many unresolved Sentry issues and regressions do I have {dr}?", ["get_error_summary"], "near_miss"),
    _t("List my top Sentry error issues {dr}, with the release each was last seen in.", ["get_error_issues"], "near_miss"),
    _t("Where do I rank on Google for '{k}'?", ["get_rankings"], date=False, extra={"keyword": ("k", KW)}),
    _t("Who outranks me on Google for '{k}'?", ["get_rankings"], date=False, extra={"keyword": ("k", KW)}),
    _t("Does Google's AI Overview quote my site for '{k}'?", ["get_ai_overview_citations"], "near_miss",
       date=False, extra={"keyword": ("k", KW)}),
    _t("What questions do people also ask about '{k}'?", ["get_related_queries"], date=False,
       extra={"keyword": ("k", KW)}),
    _t("Why did traffic to {p} drop last week?", ["explain_traffic_change"], "near_miss", date=False,
       extra={"path": ("p", PATH)}),
    # No tool can do these — the right answer is "none", not the nearest tool.
    _t("Delete this site and all of its data.", ["none"], "no_tool", date=False),
    _t("Change my account password to something stronger.", ["none"], "no_tool", date=False),
    _t("Create a new checkout funnel with three steps.", ["none"], "no_tool", date=False),
    _t("Email this week's report to my manager.", ["none"], "no_tool", date=False),
    _t("What will the weather be in Delhi tomorrow?", ["none"], "no_tool", date=False),
]

TOTAL = 80

# ── HARD tier ────────────────────────────────────────────────────────────────
# Relative dates resolved against the prompt's "today" (2026-09-01), several
# arguments at once, the registry's own "call list_sites FIRST" rule, and
# plausible-sounding requests no tool can serve.

REL_DATES = [
    ("yesterday", "custom:2026-08-31:2026-08-31"),
    ("on 15 August 2026", "custom:2026-08-15:2026-08-15"),
    ("during August 2026", "custom:2026-08-01:2026-08-31"),
    ("in the first week of August 2026 (1-7 August)", "custom:2026-08-01:2026-08-07"),
    ("in July 2026", "custom:2026-07-01:2026-07-31"),
]
SITE_NAMES = ["StudyTub", "Acme Guides", "the PixelCraft blog", "ShipFast"]
COUNTRIES = ["India", "Germany", "Brazil", "Canada"]


def _h(make_fn, tools, subgroup):
    return make_fn, tools, subgroup


def _top_pages_rel(rng):
    n, (phrase, value) = rng.choice([4, 7, 12, 15]), rng.choice(REL_DATES)
    return f"Show me the top {n} pages {phrase}.", {"limit": n, "dateRange": value}


def _countries_rel(rng):
    n, (phrase, value) = rng.choice([3, 6, 8]), rng.choice(REL_DATES)
    return f"Which {n} countries sent the most visitors {phrase}?", {"limit": n, "dateRange": value}


def _named_site(rng):
    site = rng.choice(SITE_NAMES)
    q = rng.choice([f"How is {site} doing this month?", f"Show me traffic sources for {site}.",
                    f"What are the top pages on {site} this week?"])
    return q, {}


def _rank_device_country(rng):
    kw, dev, country = rng.choice(KEYWORDS), rng.choice(["mobile", "desktop"]), rng.choice(COUNTRIES)
    return (f"Where do I rank on {dev} in {country} for '{kw}'?",
            {"keyword": kw, "device": dev, "location": country})


def _ai_country(rng):
    kw, country = rng.choice(KEYWORDS), rng.choice(COUNTRIES)
    return (f"In {country}, is Google's AI Overview for '{kw}' quoting a competitor instead of me?",
            {"keyword": kw, "location": country})


def _related_n(rng):
    kw, n = rng.choice(KEYWORDS), rng.choice([5, 8, 15])
    return f"Give me {n} related search ideas for '{kw}'.", {"keyword": kw, "limit": n}


def _explain_kw(rng):
    p, kw = rng.choice(PATHS), rng.choice(KEYWORDS)
    return (f"Explain why traffic to {p} changed, checking only the keyword '{kw}'.",
            {"path": p, "keywords": [kw]})


def _release_errors(rng):
    phrase, value = rng.choice(REL_DATES[:2])
    return (f"Signups fell after the release that went out {phrase}. Which error issues regressed, "
            "and in which release were they last seen?", {})


NONE_HARD = [
    "What was my revenue this month?",
    "Which Google Ads keywords cost me the most last week?",
    "Export every raw event from July to a CSV file.",
    "Block visitors from IP address 203.0.113.7.",
    "Rename my site to StudyTub Pro.",
    "Send an SMS to every visitor who abandoned checkout.",
    "Which of my visitors are logged-in customers, by name?",
    "Merge my two sites into one.",
]

HARD_TEMPLATES = [
    _h(_top_pages_rel, ["get_top_pages"], "hard_relative_dates"),
    _h(_countries_rel, ["get_countries"], "hard_relative_dates"),
    _h(_named_site, ["list_sites"], "hard_site_by_name"),
    _h(_rank_device_country, ["get_rankings"], "hard_multi_arg"),
    _h(_ai_country, ["get_ai_overview_citations"], "hard_multi_arg"),
    _h(_related_n, ["get_related_queries"], "hard_multi_arg"),
    _h(_explain_kw, ["explain_traffic_change"], "hard_multi_arg"),
    _h(_release_errors, ["get_error_issues"], "hard_distractor"),
]
HARD_TOTAL = 40


def _append(cases, subgroup, difficulty, question, tools, args):
    cases.append({
        "id": f"tool_{len(cases) + 1:03d}",
        "group": "tool_choice",
        "subgroup": subgroup,
        "difficulty": difficulty,
        "question": question,
        "expected_tools": tools,
        "expected_args": args,
    })


def build(seed: int = 11) -> list[dict]:
    rng = random.Random(seed)
    cases, seen = [], set()
    i = 0
    while len(cases) < TOTAL:
        make, tools, subgroup = TEMPLATES[i % len(TEMPLATES)]
        i += 1
        question, args = make(rng)
        if question in seen:
            if i > TOTAL * 20:
                raise RuntimeError("not enough distinct tool-choice questions")
            continue
        seen.add(question)
        _append(cases, subgroup, "standard", question, tools, args)

    for q in NONE_HARD:
        seen.add(q)
        _append(cases, "hard_no_tool", "hard", q, ["none"], {})
    i = 0
    while len(cases) < TOTAL + HARD_TOTAL:
        make, tools, subgroup = HARD_TEMPLATES[i % len(HARD_TEMPLATES)]
        i += 1
        question, args = make(rng)
        if question in seen:
            if i > HARD_TOTAL * 30:
                raise RuntimeError("not enough distinct hard tool-choice questions")
            continue
        seen.add(question)
        _append(cases, subgroup, "hard", question, tools, args)
    return cases
