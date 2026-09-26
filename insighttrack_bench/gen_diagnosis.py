"""Group 3 — traffic-change diagnosis cases.

Each case is built for a target subgroup, then labelled by rules.diagnose() —
the gold answer always comes from the ported engine, never from the builder's
intent. build() asserts the two agree, so a builder bug fails loudly instead of
shipping a mislabelled case.
"""
from __future__ import annotations

import random

from . import rules

DOMAINS = ["studynotes.dev", "acmeguides.io", "pixelcraft.blog", "shipfast.tools", "devlearn.net", "mealplanr.app"]
KEYWORDS = [
    "free email templates", "acid properties explained", "api rate limiting", "sql joins visual guide",
    "btech notes first year", "gdpr for developers", "react state management", "python list comprehension",
    "core web vitals guide", "docker compose tutorial", "binary search tree", "meal prep for beginners",
]
RIVALS = ["geeksforgeeks.org", "wikipedia.org", "medium.com", "dev.to", "stackoverflow.com", "w3schools.com",
          "freecodecamp.org", "hubspot.com", "reddit.com", "youtube.com"]
FEATURES = list(rules.DISPLACING_FEATURES)

# Target sizes per subgroup (total 80).
QUOTAS = {
    "single_cause": 20,
    "multi_cause": 16,
    "unexplained": 16,
    "not_significant": 16,
    "decoy": 12,
}


def _weeks(rng: random.Random, base: int, last: int, n: int = 8) -> list[int]:
    """n complete weeks: gentle noise around `base`, then `last`."""
    series = [max(0, round(base * rng.uniform(0.95, 1.05))) for _ in range(n - 2)]
    series.append(base)
    series.append(last)
    return series


def _significant_weeks(rng: random.Random, direction: str) -> list[int]:
    base = rng.randint(150, 900)
    pct = rng.uniform(0.2, 0.5)
    last = round(base * (1 - pct)) if direction == "drop" else round(base * (1 + pct))
    return _weeks(rng, base, last)


def _snapshot(position, ai_answer=False, ai_quotes=(), features=()) -> dict:
    return {
        "position": position,
        "ai_answer": bool(ai_answer),
        "ai_quotes": list(ai_quotes) if ai_answer else [],
        "features": list(features),
    }


def _quiet_serp(rng: random.Random, domain: str, page_one: bool | None = None) -> tuple[dict, dict]:
    """Before/after with nothing that counts as a cause (jitter only)."""
    top = page_one if page_one is not None else rng.random() < 0.6
    pos = rng.randint(2, 9) if top else rng.randint(13, 40)
    after = pos + rng.choice([-1, 0, 1, 2]) if top else pos + rng.choice([-2, -1, 0, 1, 2])
    after = max(1, after)
    if top and after > 10:
        after = 10
    feats = rng.sample(FEATURES, rng.randint(0, 2))
    has_ai = rng.random() < 0.5
    quotes = rng.sample(RIVALS, 2) + ([domain] if has_ai and rng.random() < 0.4 else [])
    return _snapshot(pos, has_ai, quotes, feats), _snapshot(after, has_ai, quotes, feats)


# ── one builder per scenario; each returns (weeks, before, after) ────────────

def _rank_drop(rng, domain):
    pos = rng.randint(12, 25)
    b, a = _quiet_serp(rng, domain, page_one=False)
    b["position"], a["position"] = pos, pos + rng.randint(3, 12)
    return _significant_weeks(rng, "drop"), b, a


def _page_one_exit_small(rng, domain):
    # 9 -> 11: exits page one but only a 2-place move, so rank_drop must NOT fire.
    b, a = _quiet_serp(rng, domain, page_one=True)
    b["position"], a["position"] = rng.choice([(9, 11), (10, 12), (10, 11)])
    b["features"] = a["features"] = []
    return _significant_weeks(rng, "drop"), b, a


def _ai_displacement(rng, domain):
    pos = rng.randint(1, 8)
    b = _snapshot(pos, False, [], [])
    a = _snapshot(pos + rng.choice([0, 1]), True, rng.sample(RIVALS, 3), [])
    return _significant_weeks(rng, "drop"), b, a


def _ai_citation_lost(rng, domain):
    pos = rng.randint(1, 8)
    rivals = rng.sample(RIVALS, 2)
    b = _snapshot(pos, True, rivals + [domain], [])
    a = _snapshot(pos + rng.choice([0, 1]), True, rivals + [rng.choice(RIVALS)], [])
    return _significant_weeks(rng, "drop"), b, a


def _feature_added(rng, domain):
    pos = rng.randint(1, 8)
    feat = rng.choice(FEATURES)
    b = _snapshot(pos, False, [], [])
    a = _snapshot(pos + rng.choice([0, 1]), False, [], [feat])
    return _significant_weeks(rng, "drop"), b, a


def _rank_gain(rng, domain):
    pos = rng.randint(14, 30)
    b, a = _quiet_serp(rng, domain, page_one=False)
    b["position"], a["position"] = pos, pos - rng.randint(3, 3 + (pos - 11) // 2)
    return _significant_weeks(rng, "spike"), b, a


def _citation_gained(rng, domain):
    pos = rng.randint(1, 8)
    rivals = rng.sample(RIVALS, 2)
    b = _snapshot(pos, True, rivals, [])
    a = _snapshot(pos, True, rivals + [domain], [])
    return _significant_weeks(rng, "spike"), b, a


def _feature_removed(rng, domain):
    pos = rng.randint(1, 8)
    feat = rng.choice(FEATURES)
    b = _snapshot(pos, False, [], [feat])
    a = _snapshot(pos, False, [], [])
    return _significant_weeks(rng, "spike"), b, a


def _multi_drop(rng, domain):
    # Fell off page one by 3+ AND a new AI answer quotes rivals, maybe a feature too.
    pos = rng.randint(4, 9)
    b = _snapshot(pos, False, [], [])
    a = _snapshot(pos + rng.randint(4, 15), True, rng.sample(RIVALS, 2), [])
    if rng.random() < 0.5:
        # Big move on page one + lost citation + new block.
        pos = rng.randint(1, 4)
        rivals = rng.sample(RIVALS, 2)
        b = _snapshot(pos, True, rivals + [domain], [])
        a = _snapshot(pos + rng.randint(3, 5), True, rivals, [rng.choice(FEATURES)])
    return _significant_weeks(rng, "drop"), b, a


def _multi_spike(rng, domain):
    pos = rng.randint(6, 12)
    feat = rng.choice(FEATURES)
    rivals = rng.sample(RIVALS, 2)
    b = _snapshot(pos, True, rivals, [feat])
    a = _snapshot(pos - rng.randint(3, 5), True, rivals + [domain], [])
    return _significant_weeks(rng, "spike"), b, a


def _unexplained(rng, domain):
    direction = rng.choice(["drop", "spike"])
    b, a = _quiet_serp(rng, domain)
    return _significant_weeks(rng, direction), b, a


def _not_significant(rng, domain):
    if rng.random() < 0.5:
        # Small site: a huge % on tiny numbers (6 -> 12 views).
        base = rng.randint(3, 15)
        last = base + rng.choice([-1, 1]) * rng.randint(max(1, base // 2), min(19, base * 2))
        weeks = _weeks(rng, base, max(0, last))
    else:
        # Big site: many views, small %.
        base = rng.randint(400, 2000)
        last = round(base * (1 + rng.choice([-1, 1]) * rng.uniform(0.02, 0.12)))
        weeks = _weeks(rng, base, last)
    # Search looks dramatic anyway — a temptation to invent a cause.
    pos = rng.randint(3, 8)
    b = _snapshot(pos, False, [], [])
    a = _snapshot(pos + rng.randint(3, 9), True, rng.sample(RIVALS, 2), [rng.choice(FEATURES)])
    return weeks, b, a


def _decoy(rng, domain):
    """Significant move + a search change that does NOT qualify as a cause."""
    kind = rng.choice(["jitter", "feature_off_page_one", "gain_during_drop", "new_answer_quotes_you"])
    if kind == "jitter":
        pos = rng.randint(2, 7)
        b, a = _snapshot(pos, False), _snapshot(pos + 2, False)
        return _significant_weeks(rng, "drop"), b, a
    if kind == "feature_off_page_one":
        pos = rng.randint(14, 30)
        b = _snapshot(pos, False, [], [])
        a = _snapshot(pos + rng.choice([-1, 0, 1]), False, [], [rng.choice(FEATURES)])
        return _significant_weeks(rng, "drop"), b, a
    if kind == "gain_during_drop":
        pos = rng.randint(14, 25)
        b, a = _snapshot(pos, False), _snapshot(pos - rng.randint(3, 3), False)
        return _significant_weeks(rng, "drop"), b, a
    # A brand-new AI answer that DOES quote the site, during a drop.
    pos = rng.randint(1, 6)
    b = _snapshot(pos, False)
    a = _snapshot(pos, True, rng.sample(RIVALS, 1) + [domain], [])
    return _significant_weeks(rng, "drop"), b, a


BUILDERS = {
    "single_cause": [_rank_drop, _page_one_exit_small, _ai_displacement, _ai_citation_lost,
                     _feature_added, _rank_gain, _citation_gained, _feature_removed],
    "multi_cause": [_multi_drop, _multi_spike],
    "unexplained": [_unexplained],
    "not_significant": [_not_significant],
    "decoy": [_decoy],
}


def _category(gold: dict) -> str:
    if not gold["significant"]:
        return "not_significant"
    if gold["causes"] == ["unexplained_by_serp"]:
        return "unexplained"  # decoys also land here
    return "single_cause" if len(gold["causes"]) == 1 else "multi_cause"


# ── HARD tier ────────────────────────────────────────────────────────────────
# Each hard builder returns (weeks, [(before, after), ...], intended_gold). The
# ported rules must agree with the intent, or the build fails — so these cases
# check the reasoning written here as well as the rules.

def _fixed_weeks(rng, previous: int, last: int) -> list[int]:
    return _weeks(rng, previous, last)


def _sig(direction, causes):
    return {"significant": True, "direction": direction, "causes": sorted(causes)}


NOT_SIG = {"significant": False, "direction": None, "causes": []}


def _h_mixed_keywords(rng, domain, v):
    """Several keywords pull in different directions; only some count."""
    if v % 2 == 0:
        a, b = rng.randint(12, 16), rng.randint(20, 25)
        loser = (_snapshot(a), _snapshot(a + rng.randint(3, 6)))
        # A gain and a new citation on the other keyword do not count on a drop.
        rivals = rng.sample(RIVALS, 2)
        winner = (_snapshot(b, True, rivals), _snapshot(b - rng.randint(3, 6), True, rivals + [domain]))
        return _significant_weeks(rng, "drop"), [loser, winner], _sig("drop", ["rank_drop"])
    a, b = rng.randint(14, 20), rng.randint(14, 30)
    winner = (_snapshot(a), _snapshot(a - rng.randint(3, 3)))
    # A removed block off page one does not count.
    feat = rng.choice(FEATURES)
    other = (_snapshot(b, features=[feat]), _snapshot(b, features=[]))
    return _significant_weeks(rng, "spike"), [winner, other], _sig("spike", ["rank_gain"])


def _h_boundary(rng, domain, v):
    """Every threshold hit exactly: 15%, 20 views, 3 places, position 10."""
    q = v % 8
    if q == 0:  # exactly -15% and 30 views -> significant; exactly 3 places -> cause
        return _fixed_weeks(rng, 200, 170), [(_snapshot(12), _snapshot(15))], _sig("drop", ["rank_drop"])
    if q == 1:  # -14.5% -> not significant, however dramatic search looks
        return _fixed_weeks(rng, 200, 171), [(_snapshot(3), _snapshot(9))], NOT_SIG
    if q == 2:  # -20% and exactly 20 views -> significant; 2 places is jitter
        return _fixed_weeks(rng, 100, 80), [(_snapshot(5), _snapshot(7))], _sig("drop", ["unexplained_by_serp"])
    if q == 3:  # 19 views -> not significant even at 19%
        return _fixed_weeks(rng, 100, 81), [(_snapshot(4), _snapshot(12))], NOT_SIG
    if q == 4:  # exactly +15%; exactly 3 places up
        return _fixed_weeks(rng, 400, 460), [(_snapshot(14), _snapshot(11))], _sig("spike", ["rank_gain"])
    if q == 5:  # 10 -> 11 leaves page one with a 1-place move
        return _significant_weeks(rng, "drop"), [(_snapshot(10), _snapshot(11))], _sig("drop", ["page_one_exit"])
    if q == 6:  # 11 -> 13: 2 places, never on page one
        return _significant_weeks(rng, "drop"), [(_snapshot(11), _snapshot(13))], _sig("drop", ["unexplained_by_serp"])
    # 11 -> 10 is not a cause, but #10 IS page one, so the removed block counts
    feat = rng.choice(FEATURES)
    return (_significant_weeks(rng, "spike"), [(_snapshot(11, features=[feat]), _snapshot(10))],
            _sig("spike", ["serp_feature_removed"]))


def _h_domain_match(rng, domain, v):
    """Is the site quoted? Subdomains and www count; lookalike domains do not."""
    stem, tld = domain.split(".", 1)
    lookalike = f"get{stem}.{tld}"  # e.g. getdevlearn.net — a different site
    rivals = rng.sample(RIVALS, 2)
    q = v % 4
    if q == 0:
        before = _snapshot(3, True, rivals + [f"blog.{domain}"])
        after = _snapshot(3, True, rivals + [lookalike])
        return _significant_weeks(rng, "drop"), [(before, after)], _sig("drop", ["ai_citation_lost"])
    if q == 1:
        before, after = _snapshot(4), _snapshot(4, True, rivals[:1] + [f"www.{domain}"])
        return _significant_weeks(rng, "drop"), [(before, after)], _sig("drop", ["unexplained_by_serp"])
    if q == 2:
        before, after = _snapshot(4), _snapshot(4, True, rivals[:1] + [lookalike])
        return _significant_weeks(rng, "drop"), [(before, after)], _sig("drop", ["ai_overview_displacement"])
    before = _snapshot(5, True, rivals + [lookalike])
    after = _snapshot(5, True, rivals + [f"docs.{domain}"])
    return _significant_weeks(rng, "spike"), [(before, after)], _sig("spike", ["ai_citation_gained"])


def _h_not_ranking(rng, domain, v):
    """Position null means 'not ranking' — rank moves need a rank both times."""
    q = v % 4
    if q == 0:  # page one -> gone: exits page one, but is not a 'rank_drop'
        return _significant_weeks(rng, "drop"), [(_snapshot(7), _snapshot(None))], _sig("drop", ["page_one_exit"])
    if q == 1:  # #15 -> gone: neither rule applies
        return _significant_weeks(rng, "drop"), [(_snapshot(15), _snapshot(None))], _sig("drop", ["unexplained_by_serp"])
    if q == 2:  # never ranked, but a new AI answer now quotes rivals
        after = _snapshot(None, True, rng.sample(RIVALS, 2))
        return (_significant_weeks(rng, "drop"), [(_snapshot(None), after)],
                _sig("drop", ["ai_overview_displacement"]))
    # not ranking -> #6 during a spike: no 'rank_gain' without a previous rank
    return _significant_weeks(rng, "spike"), [(_snapshot(None), _snapshot(6))], _sig("spike", ["unexplained_by_serp"])


def _h_spike_with_losses(rng, domain, v):
    """'any' causes still count when traffic went UP."""
    q = v % 4
    if q == 0:
        a, b = rng.randint(12, 15), rng.randint(20, 26)
        return (_significant_weeks(rng, "spike"),
                [(_snapshot(a), _snapshot(a + rng.randint(4, 8))), (_snapshot(b), _snapshot(b - rng.randint(3, 6)))],
                _sig("spike", ["rank_drop", "rank_gain"]))
    if q == 1:
        rivals = rng.sample(RIVALS, 2)
        before, after = _snapshot(4, True, rivals + [domain]), _snapshot(4, True, rivals)
        return _significant_weeks(rng, "spike"), [(before, after)], _sig("spike", ["ai_citation_lost"])
    if q == 2:  # a new block on a spike is ignored; a removed one on page one counts
        f1, f2 = rng.sample(FEATURES, 2)
        return (_significant_weeks(rng, "spike"),
                [(_snapshot(3), _snapshot(3, features=[f1])), (_snapshot(6, features=[f2]), _snapshot(6))],
                _sig("spike", ["serp_feature_removed"]))
    # 9 -> 11: leaves page one by 2 places, so page_one_exit without rank_drop
    return _significant_weeks(rng, "spike"), [(_snapshot(9), _snapshot(11))], _sig("spike", ["page_one_exit"])


HARD_BUILDERS = {
    "hard_mixed_keywords": _h_mixed_keywords,
    "hard_boundary": _h_boundary,
    "hard_domain_match": _h_domain_match,
    "hard_not_ranking": _h_not_ranking,
    "hard_spike_with_losses": _h_spike_with_losses,
}
HARD_QUOTA = 8  # per hard subgroup -> 40


def _case(cases, subgroup, difficulty, scenario, domain, weeks, pairs, rng):
    keywords = rng.sample(KEYWORDS, len(pairs))
    kws = [{"keyword": k, "before": b, "after": a} for k, (b, a) in zip(keywords, pairs)]
    findings = [rules.derive_finding(k["keyword"], domain, k["before"], k["after"]) for k in kws]
    return {
        "id": f"diag_{len(cases) + 1:03d}",
        "group": "diagnosis",
        "subgroup": subgroup,
        "difficulty": difficulty,
        "scenario": scenario,
        "domain": domain,
        "weeks": weeks,
        "keywords": kws,
        "gold": rules.diagnose(weeks, findings),
    }


def build(seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []
    for subgroup, quota in QUOTAS.items():
        made, attempts = 0, 0
        while made < quota:
            attempts += 1
            if attempts > quota * 50:
                raise RuntimeError(f"could not build {subgroup} cases")
            builder = BUILDERS[subgroup][made % len(BUILDERS[subgroup])]
            domain = rng.choice(DOMAINS)
            weeks, before, after = builder(rng, domain)
            case = _case(cases, subgroup, "standard", builder.__name__.lstrip("_"), domain, weeks, [(before, after)], rng)
            expected = "unexplained" if subgroup == "decoy" else subgroup
            if _category(case["gold"]) != expected:
                continue  # random draw landed elsewhere; the gold stays authoritative
            cases.append(case)
            made += 1

    for subgroup, builder in HARD_BUILDERS.items():
        for v in range(HARD_QUOTA):
            domain = rng.choice(DOMAINS)
            weeks, pairs, intended = builder(rng, domain, v)
            case = _case(cases, subgroup, "hard", f"{subgroup}_{v}", domain, weeks, pairs, rng)
            if case["gold"] != intended:
                raise AssertionError(f"{subgroup} v{v}: rules say {case['gold']}, builder intended {intended}")
            cases.append(case)
    return cases
