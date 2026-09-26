"""The built dataset: reproducible, balanced, and every gold answer re-derivable."""
import filecmp
import json
import os

import pytest

from insighttrack_bench import build, rules
from insighttrack_bench.scoring import GROUPS


def load(dataset, group):
    with open(os.path.join(dataset, f"cases_{group}.jsonl")) as fh:
        return [json.loads(line) for line in fh]


def test_rebuild_is_byte_identical(dataset, tmp_path):
    build.build(str(tmp_path), "tester")
    for name in os.listdir(dataset):
        assert filecmp.cmp(os.path.join(dataset, name), os.path.join(tmp_path, name), shallow=False), name


@pytest.mark.parametrize("group", GROUPS)
def test_each_group_has_80_standard_and_40_hard_cases(dataset, group):
    cases = load(dataset, group)
    assert len({c["id"] for c in cases}) == len(cases) == 120
    assert all(c["group"] == group for c in cases)
    assert sum(c["difficulty"] == "standard" for c in cases) == 80
    hard = [c for c in cases if c["difficulty"] == "hard"]
    assert len(hard) == 40
    # Hard cases are labelled, so results can be split by tier.
    assert all(c["subgroup"].startswith("hard_") for c in hard)
    assert not any(c["subgroup"].startswith("hard_") for c in cases if c["difficulty"] == "standard")


def test_manifest_matches_files(dataset):
    manifest = json.load(open(os.path.join(dataset, "manifest.json")))
    for group in GROUPS:
        assert manifest["groups"][group]["cases"] == len(load(dataset, group))


# ── diagnosis ────────────────────────────────────────────────────────────────

def test_diagnosis_gold_is_recomputable(dataset):
    for c in load(dataset, "diagnosis"):
        findings = [rules.derive_finding(k["keyword"], c["domain"], k["before"], k["after"]) for k in c["keywords"]]
        assert rules.diagnose(c["weeks"], findings) == c["gold"], c["id"]


def test_diagnosis_subgroups_mean_what_they_say(dataset):
    for c in load(dataset, "diagnosis"):
        g, sub = c["gold"], c["subgroup"]
        if sub == "not_significant":
            assert not g["significant"]
        elif sub in ("unexplained", "decoy"):
            assert g["causes"] == ["unexplained_by_serp"]
        elif sub == "single_cause":
            assert len(g["causes"]) == 1 and g["causes"] != ["unexplained_by_serp"]
        elif sub == "multi_cause":
            assert len(g["causes"]) >= 2


def test_diagnosis_covers_every_cause_code(dataset):
    seen = {code for c in load(dataset, "diagnosis") for code in c["gold"]["causes"]}
    assert seen == set(rules.CAUSE_CODES)


def test_not_significant_cases_still_tempt_with_search_changes(dataset):
    # The point of these cases: search DID change, and the right answer is still "nothing".
    for c in load(dataset, "diagnosis"):
        if c["subgroup"] == "not_significant":
            k = c["keywords"][0]
            assert k["before"]["position"] != k["after"]["position"] or k["after"]["features"]


# ── tool choice ──────────────────────────────────────────────────────────────

def test_expected_tools_exist(dataset, its):
    names = its.tool_names() | {"none"}
    for c in load(dataset, "tool_choice"):
        assert set(c["expected_tools"]) <= names, c["id"]


def test_expected_args_are_real_parameters(dataset, its):
    tools = {t["name"]: t for t in its._STATE["tools"]}
    for c in load(dataset, "tool_choice"):
        if c["expected_tools"] == ["none"]:
            assert c["expected_args"] == {}
            continue
        for tool in c["expected_tools"]:
            props = tools[tool]["inputSchema"].get("properties", {})
            assert set(c["expected_args"]) <= set(props), (c["id"], tool)


def test_every_tool_is_exercised(dataset, its):
    used = {t for c in load(dataset, "tool_choice") for t in c["expected_tools"]}
    assert its.tool_names() <= used


# ── data reading ─────────────────────────────────────────────────────────────

def test_data_reading_answers_are_well_formed(dataset):
    cases = load(dataset, "data_reading")
    for c in cases:
        if c["answer_type"] == "number":
            assert isinstance(c["answer"], (int, float))
        elif c["answer_type"] == "text":
            assert isinstance(c["answer"], str)
            assert c["answer"] in ("yes", "no") or c["answer"] in json.dumps(c["tool_output"])
        else:
            assert c["answer"] == "not_available"
    share = sum(c["answer_type"] == "unavailable" for c in cases) / len(cases)
    assert 0.2 <= share <= 0.35


# ── SQL ──────────────────────────────────────────────────────────────────────

def test_reference_sql_reproduces_expected_on_the_shipped_tables(dataset, its):
    for c in load(dataset, "sql"):
        assert its.check_sql(c["reference_sql"]) is None, c["id"]
        assert its.rows_equal(its.run_sql(c["reference_sql"]), c["expected"], c["ordered"]), c["id"]


def test_sql_answers_are_not_trivial(dataset):
    for c in load(dataset, "sql"):
        assert c["expected"] and c["expected"] != [[0]] and c["expected"] != [[None]], c["id"]


def test_hard_diagnosis_uses_several_keywords_and_every_edge(dataset):
    hard = [c for c in load(dataset, "diagnosis") if c["difficulty"] == "hard"]
    assert any(len(c["keywords"]) > 1 for c in hard)
    # Exact thresholds really are exact.
    weeks = [c["weeks"][-2:] for c in hard if c["subgroup"] == "hard_boundary"]
    assert [200, 170] in weeks and [100, 80] in weeks and [400, 460] in weeks


def test_hard_exact_share_defeats_the_rounded_field(dataset):
    for c in load(dataset, "data_reading"):
        if c["question"].startswith("What exact share"):
            src = c["question"].split("came from ")[1].split("?")[0]
            row = next(r for r in c["tool_output"]["data"] if r["source"] == src)
            assert abs(row["percentage"] - c["answer"]) > c["tolerance"]


def test_hard_top_pages_questions_show_the_limit(dataset):
    for c in load(dataset, "data_reading"):
        if c["tool"] == "get_top_pages":
            assert c["tool_args"]["limit"] == 10
