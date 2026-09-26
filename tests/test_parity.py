"""The Python answer key must agree with InsightTrack's JavaScript engine.

Runs scripts/parity.mjs (which imports the product's correlationService.js) on
every benchmark case plus 1,500 random fuzz cases with 1-3 keywords each. Skips when InsightTrack or
Node is not available.
"""
import json
import os
import random
import subprocess

import pytest

from conftest import INSIGHTTRACK_API, ROOT, insighttrack_available
from insighttrack_bench import gen_diagnosis, rules

pytestmark = pytest.mark.skipif(not insighttrack_available(), reason="InsightTrack backend or node not found")


def run_js(cases):
    proc = subprocess.run(
        ["node", os.path.join(ROOT, "scripts", "parity.mjs")],
        input=json.dumps(cases), capture_output=True, text=True, timeout=120,
        env={**os.environ, "INSIGHTTRACK_API": INSIGHTTRACK_API},
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def python_gold(c):
    findings = [rules.derive_finding(k["keyword"], c["domain"], k["before"], k["after"]) for k in c["keywords"]]
    return rules.diagnose(c["weeks"], findings)


def fuzz_cases(n, seed=99):
    rng = random.Random(seed)
    feats = list(rules.DISPLACING_FEATURES) + ["ai_overview"]
    quotes = ["me.com", "blog.me.com", "www.me.com", "getme.com", "me.com.evil.io", "rival.com"]

    def snap():
        ai = rng.random() < 0.5
        return {
            "position": None if rng.random() < 0.15 else rng.randint(1, 30),
            "ai_answer": ai,
            "ai_quotes": rng.sample(quotes, rng.randint(0, 3)) if ai else [],
            "features": rng.sample(feats, rng.randint(0, 3)),
        }

    out = []
    for _ in range(n):
        base = rng.choice([rng.randint(0, 40), rng.randint(50, 2000)])
        last = max(0, round(base * rng.uniform(0.3, 1.8)))
        keywords = [{"keyword": f"kw{i}", "before": snap(), "after": snap()} for i in range(rng.randint(1, 3))]
        out.append({"domain": "me.com", "weeks": [base, base, last], "keywords": keywords})
    return out


def test_every_benchmark_case_matches_the_product():
    cases = gen_diagnosis.build(7)
    js = run_js(cases)
    for c, j in zip(cases, js):
        assert c["gold"] == j, c["id"]


def test_random_inputs_match_the_product():
    cases = fuzz_cases(1500)
    js = run_js(cases)
    mismatches = [(c, python_gold(c), j) for c, j in zip(cases, js) if python_gold(c) != j]
    assert not mismatches, mismatches[:3]
