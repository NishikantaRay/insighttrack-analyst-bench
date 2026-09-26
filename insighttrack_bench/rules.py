"""Answer key for the diagnosis task.

A line-by-line Python port of InsightTrack's correlation engine
(`apps/analytics-api/src/services/correlationService.js`) and the finding
derivation in `searchVisibilityService.checkKeyword()`. Pure functions, no I/O.

tests/test_parity.py runs the original JavaScript on the same inputs and fails
if the two ever disagree, so this file cannot drift silently from the product.
"""
from __future__ import annotations

import math

# Significance floors — BOTH must clear (correlationService.js).
MIN_CHANGE_PCT = 15.0
MIN_CHANGE_ABS = 20

# A rank move of this many places is a cause, not SERP jitter.
RANK_MOVE_THRESHOLD = 3
PAGE_ONE = 10

# Result-page blocks that take clicks from organic listings. The AI Overview is
# deliberately excluded: it has its own citation rules.
DISPLACING_FEATURES = (
    "featured_snippet",
    "people_also_ask",
    "videos",
    "shopping",
    "knowledge_graph",
)

# Every code the engine can emit, in a stable order for prompts and reports.
CAUSE_CODES = (
    "rank_drop",
    "page_one_exit",
    "ai_overview_displacement",
    "ai_citation_lost",
    "serp_feature_added",
    "rank_gain",
    "ai_citation_gained",
    "serp_feature_removed",
    "unexplained_by_serp",
)
SERP_CAUSES = tuple(c for c in CAUSE_CODES if c != "unexplained_by_serp")


def _js_round1(x: float) -> float:
    """JavaScript Math.round(x * 10) / 10 (half rounds toward +infinity)."""
    return math.floor(x * 10 + 0.5) / 10


def domain_matches(candidate: str | None, target: str | None) -> bool:
    """Same site: the host itself or any subdomain of it (normalize.js)."""
    if not candidate or not target:
        return False
    c = str(candidate).lower().removeprefix("www.")
    t = str(target).lower().removeprefix("www.")
    return c == t or c.endswith("." + t)


def detect_change(weeks: list[int], exclude_partial: bool = False) -> dict:
    """Week-over-week change of the last two weeks (detectChange).

    The benchmark only ever shows complete weeks, so it calls this with
    exclude_partial=False; the product drops the in-progress week first.
    """
    series = weeks[:-1] if exclude_partial and len(weeks) > 2 else list(weeks)
    if len(series) < 2:
        return {"significant": False, "direction": "unknown", "change_pct": None, "change_abs": None}

    current, previous = series[-1], series[-2]
    change_abs = current - previous
    if previous == 0:
        change_pct = 100.0 if current > 0 else 0.0
    else:
        change_pct = change_abs / previous * 100

    significant = abs(change_pct) >= MIN_CHANGE_PCT and abs(change_abs) >= MIN_CHANGE_ABS
    direction = "drop" if change_abs < 0 else "spike" if change_abs > 0 else "flat"
    return {
        "significant": significant,
        "direction": direction,
        "change_pct": _js_round1(change_pct),
        "change_abs": change_abs,
        "previous_week": previous,
        "current_week": current,
    }


def citation_change(before: dict, after: dict, domain: str) -> tuple[str, bool]:
    """(citationChange, domainIsCited) exactly as checkKeyword() derives them."""
    cited_now = any(domain_matches(d, domain) for d in after.get("ai_quotes", []))
    cited_before = any(domain_matches(d, domain) for d in before.get("ai_quotes", []))
    if not before.get("ai_answer") and after.get("ai_answer"):
        change = "new_overview"
    elif cited_before and not cited_now:
        change = "lost"
    elif not cited_before and cited_now:
        change = "gained"
    else:
        change = "unchanged"
    return change, cited_now


def serp_diff(before: dict, after: dict) -> dict:
    """Displacing features that appeared or vanished (serpDiff, features half)."""
    was, now = set(before.get("features", [])), set(after.get("features", []))
    return {
        "features_added": [f for f in after.get("features", []) if f in DISPLACING_FEATURES and f not in was],
        "features_removed": [f for f in before.get("features", []) if f in DISPLACING_FEATURES and f not in now],
    }


def derive_finding(keyword: str, domain: str, before: dict, after: dict) -> dict:
    """The keyword finding the engine attributes, built from two snapshots."""
    change, cited_now = citation_change(before, after, domain)
    diff = serp_diff(before, after)
    return {
        "keyword": keyword,
        "previous_position": before.get("position"),
        "position": after.get("position"),
        "citation_change": change,
        "domain_is_cited": cited_now,
        **diff,
    }


def attribute_keyword(f: dict, direction: str) -> list[str]:
    """Cause codes for ONE keyword's evidence (attributeKeyword), in rule order."""
    causes: list[str] = []
    prev, curr = f.get("previous_position"), f.get("position")
    moved = prev - curr if prev is not None and curr is not None else None  # +ve = improved

    if moved is not None and moved <= -RANK_MOVE_THRESHOLD:
        causes.append("rank_drop")
    if prev is not None and prev <= PAGE_ONE and (curr is None or curr > PAGE_ONE):
        causes.append("page_one_exit")
    if f.get("citation_change") == "new_overview" and not f.get("domain_is_cited"):
        causes.append("ai_overview_displacement")
    if f.get("citation_change") == "lost":
        causes.append("ai_citation_lost")

    on_page_one = curr is not None and curr <= PAGE_ONE
    if direction == "drop" and on_page_one and f.get("features_added"):
        causes.append("serp_feature_added")

    if direction == "spike":
        if on_page_one and f.get("features_removed"):
            causes.append("serp_feature_removed")
        if moved is not None and moved >= RANK_MOVE_THRESHOLD:
            causes.append("rank_gain")
        if f.get("citation_change") == "gained":
            causes.append("ai_citation_gained")
    return causes


def diagnose(weeks: list[int], findings: list[dict]) -> dict:
    """The gold answer: significance, direction and the set of cause codes."""
    traffic = detect_change(weeks)
    if not traffic["significant"]:
        return {"significant": False, "direction": None, "causes": []}

    causes: list[str] = []
    for f in findings:
        for c in attribute_keyword(f, traffic["direction"]):
            if c not in causes:
                causes.append(c)
    # Rule 7 — traffic moved and search did not: an honest "not search".
    if not causes:
        causes = ["unexplained_by_serp"]
    return {"significant": True, "direction": traffic["direction"], "causes": sorted(causes)}
