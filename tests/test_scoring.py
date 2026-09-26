"""Graders: a perfect model scores 100%, wrong answers score 0, failure modes are flagged."""
import json
import os

import pytest

from insighttrack_bench.scoring import GROUPS


def cases(dataset, group):
    with open(os.path.join(dataset, f"cases_{group}.jsonl")) as fh:
        return [json.loads(line) for line in fh]


def oracle(case):
    """The reply a perfect model would give."""
    g = case["group"]
    if g == "tool_choice":
        return json.dumps({"tool": case["expected_tools"][0], "arguments": case["expected_args"]})
    if g == "data_reading":
        return json.dumps({"answer": case["answer"]})
    if g == "diagnosis":
        return json.dumps(case["gold"])
    return f"```sql\n{case['reference_sql']}\n```"


@pytest.mark.parametrize("group", GROUPS)
def test_perfect_answers_score_100_percent(dataset, its, group):
    results = [its.score(c, oracle(c)) for c in cases(dataset, group)]
    failed = [r["id"] for r in results if not r["correct"]]
    assert not failed
    assert its.aggregate(results, len(results)) == (1.0, 0.0)


@pytest.mark.parametrize("group", GROUPS)
def test_prompts_render_and_carry_the_question(dataset, its, group):
    for c in cases(dataset, group):
        p = its.build_prompt(c)
        assert "Pulse" in p and len(p) < 20_000
        if "question" in c:
            assert c["question"] in p


@pytest.mark.parametrize("group", GROUPS)
def test_garbage_scores_zero(dataset, its, group):
    for c in cases(dataset, group)[:20]:
        assert its.score(c, "I am not sure, sorry.")["correct"] is False


# ── parsing ──────────────────────────────────────────────────────────────────

def test_json_is_found_inside_fences_and_prose(its):
    assert its.extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert its.extract_json('Answer: {"a": {"b": "}"}} done') == {"a": {"b": "}"}}
    assert its.extract_json("no json here") is None
    assert its.extract_json({"a": 1}) == {"a": 1}


def test_sql_is_found_in_fences_or_bare(its):
    assert its.extract_sql("```sql\nSELECT 1\n```") == "SELECT 1"
    assert its.extract_sql("SELECT 1") == "SELECT 1"


# ── tool choice ──────────────────────────────────────────────────────────────

def test_tool_choice_flags_invented_tools_and_checks_args(dataset, its):
    c = next(c for c in cases(dataset, "tool_choice") if "path" in c["expected_args"])
    wrong_path = dict(c["expected_args"], path="/nope")
    assert its.score(c, json.dumps({"tool": c["expected_tools"][0], "arguments": wrong_path}))["correct"] is False
    no_slash = dict(c["expected_args"], path=c["expected_args"]["path"].lstrip("/"))
    assert its.score(c, json.dumps({"tool": c["expected_tools"][0], "arguments": no_slash}))["correct"] is True
    r = its.score(c, json.dumps({"tool": "get_everything", "arguments": {}}))
    assert r["invalid_tool"] and not r["correct"]


def test_no_tool_cases_reject_the_nearest_tool(dataset, its):
    c = next(c for c in cases(dataset, "tool_choice") if c["subgroup"] == "no_tool")
    assert its.score(c, '{"tool": "list_sites", "arguments": {}}')["correct"] is False
    assert its.score(c, '{"tool": "none", "arguments": {}}')["correct"] is True


# ── data reading ─────────────────────────────────────────────────────────────

def test_inventing_a_number_is_flagged_as_fabrication(dataset, its):
    c = next(c for c in cases(dataset, "data_reading") if c["answer_type"] == "unavailable")
    r = its.score(c, '{"answer": 42.5}')
    assert r["fabricated"] and not r["correct"]
    right = its.score(c, '{"answer": "not available"}')
    assert right["correct"] and not right["refused"]  # a correct "not available" is not a refusal


def test_numbers_respect_tolerance_and_formatting(dataset, its):
    c = next(c for c in cases(dataset, "data_reading") if c["answer_type"] == "number" and c["tolerance"] == 0.01)
    assert its.score(c, json.dumps({"answer": f"{c['answer']}"}))["correct"]
    assert its.score(c, json.dumps({"answer": c["answer"] + 0.05}))["correct"] is False
    big = next(c for c in cases(dataset, "data_reading") if c["answer_type"] == "number" and abs(c["answer"]) >= 1000)
    assert its.score(big, json.dumps({"answer": f"{big['answer']:,}"}))["correct"]


def test_refusing_an_answerable_question_is_wrong(dataset, its):
    c = next(c for c in cases(dataset, "data_reading") if c["answer_type"] == "number")
    r = its.score(c, '{"answer": "not_available"}')
    assert r["refused"] and not r["correct"]


# ── diagnosis ────────────────────────────────────────────────────────────────

def test_blaming_search_for_noise_is_an_invented_cause(dataset, its):
    c = next(c for c in cases(dataset, "diagnosis") if c["subgroup"] == "not_significant")
    r = its.score(c, '{"significant": true, "direction": "drop", "causes": ["rank_drop"]}')
    assert r["invented_cause"] and r["missed_significance"] and not r["correct"]


def test_blaming_search_for_a_decoy_is_an_invented_cause(dataset, its):
    c = next(c for c in cases(dataset, "diagnosis") if c["subgroup"] == "decoy")
    wrong = dict(c["gold"], causes=["rank_drop"])
    r = its.score(c, json.dumps(wrong))
    assert r["invented_cause"] and not r["correct"]


def test_diagnosis_needs_the_exact_cause_set(dataset, its):
    c = next(c for c in cases(dataset, "diagnosis") if c["subgroup"] == "multi_cause")
    partial = dict(c["gold"], causes=c["gold"]["causes"][:1])
    assert its.score(c, json.dumps(partial))["correct"] is False
    shuffled = dict(c["gold"], causes=list(reversed(c["gold"]["causes"])))
    assert its.score(c, json.dumps(shuffled))["correct"] is True


# ── SQL safety + comparison ──────────────────────────────────────────────────

@pytest.mark.parametrize("sql", [
    "DROP TABLE events",
    "SELECT 1; DROP TABLE events",
    "DELETE FROM events",
    "COPY events TO 'x.csv'",
    "ATTACH 'x.db'",
    "SET enable_external_access = true",
    "",
])
def test_unsafe_sql_is_refused(its, sql):
    assert its.check_sql(sql) is not None


def test_sql_cannot_read_files(its):
    with pytest.raises(Exception):
        its.run_sql("SELECT * FROM read_csv('/etc/hosts')")


def test_tables_survive_every_attempt(its):
    before = its.run_sql("SELECT COUNT(*) FROM events")
    for bad in ("DELETE FROM events", "DROP TABLE events"):
        with pytest.raises(ValueError):
            its.run_sql(bad)
    assert its.run_sql("SELECT COUNT(*) FROM events") == before


def test_forbidden_words_inside_strings_are_fine(its):
    assert its.check_sql("SELECT COUNT(*) FROM events WHERE path = '/update'") is None


def test_row_comparison(its):
    assert its.rows_equal([(1, "a"), (2, "b")], [[2, "b"], [1, "a"]], ordered=False)
    assert not its.rows_equal([(1, "a"), (2, "b")], [[2, "b"], [1, "a"]], ordered=True)
    assert its.rows_equal([(33.33,)], [[33.3]], ordered=True)
    assert not its.rows_equal([(1, "a")], [[1]], ordered=True)  # extra column


def test_a_sql_query_with_wrong_logic_scores_zero(dataset, its):
    c = next(c for c in cases(dataset, "sql") if c["subgroup"] == "page_views")
    wrong = c["reference_sql"].replace("type = 'pageview'", "type = 'custom'")
    assert its.score(c, wrong)["correct"] is False


def test_aggregate_counts_missing_runs_as_wrong(its):
    acc, se = its.aggregate([{"correct": True}] * 3, total=4)
    assert acc == 0.75 and se > 0


# ── retrying the model call ──────────────────────────────────────────────────

class RateLimitError(Exception):
    pass


class BadRequestError(Exception):
    pass


def test_transient_errors_are_retried_with_backoff(its):
    calls, waits = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RateLimitError("The model is currently experiencing heavy load")
        return "ok"

    assert its.call_with_retry(flaky, sleep=waits.append) == "ok"
    assert len(calls) == 3 and waits == [5.0, 10.0]


def test_real_errors_are_not_retried(its):
    calls = []

    def broken():
        calls.append(1)
        raise BadRequestError("bad prompt")

    with pytest.raises(BadRequestError):
        its.call_with_retry(broken, sleep=lambda s: None)
    assert len(calls) == 1


def test_retries_give_up_eventually(its):
    def always_busy():
        raise RateLimitError("busy")

    waits = []
    with pytest.raises(RateLimitError):
        its.call_with_retry(always_busy, attempts=4, sleep=waits.append)
    assert waits == [5.0, 10.0, 20.0]


def test_a_small_limit_samples_every_subgroup(dataset, its):
    few = its.load_cases(dataset, "diagnosis", limit=5)
    assert len(few) == 5
    assert len({c["subgroup"] for c in few}) == 5


def test_cases_can_be_filtered_by_difficulty(dataset, its):
    hard = its.load_cases(dataset, "sql", difficulty="hard")
    assert len(hard) == 40 and all(c["difficulty"] == "hard" for c in hard)
    assert len(its.load_cases(dataset, "sql", difficulty="hard", limit=7)) == 7


def test_breakdown_splits_by_tier(its):
    out = its.breakdown([{"correct": True, "subgroup": "a", "difficulty": "standard"},
                         {"correct": False, "subgroup": "hard_b", "difficulty": "hard"}])
    assert out["TIER standard"] == {"n": 1, "correct": 1}
    assert out["TIER hard"] == {"n": 1, "correct": 0}


def test_postgres_json_operator_habit_fails_on_duckdb(dataset, its):
    """Seen on Kaggle: `props->>'name' = 'x'` parses as `props ->> ('name' = 'x')` in DuckDB."""
    c = next(c for c in cases(dataset, "sql") if c["subgroup"] == "custom_events")
    name = c["reference_sql"].split("'$.name') = '")[1].split("'")[0]
    date_cond = c["reference_sql"].split("AND CAST(")[1]
    postgres_style = f"SELECT COUNT(*) FROM events WHERE type = 'custom' AND properties->>'name' = '{name}' AND CAST({date_cond}"
    r = its.score(c, postgres_style)
    assert r["correct"] is False and r["error"] == "ConversionException"
    parenthesised = postgres_style.replace("properties->>'name' =", "(properties->>'name') =")
    assert its.score(c, parenthesised)["correct"] is True


# ── capped output (Kaggle prices calls by their MAXIMUM output) ──────────────

class BadRequestError(Exception):
    status_code = 400


class FakeLLM:
    def __init__(self, reject=()):
        self.reject, self.calls = set(reject), []

    def prompt(self, text, extra_api_params=None):
        self.calls.append(extra_api_params)
        key = next(iter(extra_api_params)) if extra_api_params else None
        if key in self.reject:
            raise BadRequestError(f"Unsupported parameter: '{key}'")
        return "ok"


def test_ask_caps_the_output_length(its):
    llm = FakeLLM()
    assert its.ask(llm, "hi") == "ok"
    assert llm.calls == [{"max_completion_tokens": its.MAX_OUTPUT_TOKENS}]


def test_ask_falls_back_when_a_provider_rejects_the_parameter(its):
    llm = FakeLLM(reject={"max_completion_tokens"})
    assert its.ask(llm, "hi") == "ok"
    assert llm.calls == [{"max_completion_tokens": its.MAX_OUTPUT_TOKENS}, {"max_tokens": its.MAX_OUTPUT_TOKENS}]
    llm = FakeLLM(reject={"max_completion_tokens", "max_tokens"})
    assert its.ask(llm, "hi") == "ok" and llm.calls[-1] is None


def test_ask_does_not_hide_quota_errors(its):
    class PermissionDeniedError(Exception):
        status_code = 403

    class Broke(FakeLLM):
        def prompt(self, text, extra_api_params=None):
            raise PermissionDeniedError("estimated cost exceeds your available quota")

    with pytest.raises(PermissionDeniedError):
        its.ask(Broke(), "hi", sleep=lambda s: None)
