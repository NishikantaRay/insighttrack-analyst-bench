"""Prompts and graders for InsightTrack Analyst Bench.

This file is copied into the Kaggle dataset as `itbench_scoring.py`, so the
Kaggle task files and the local tests run exactly the same code. It depends on
the standard library only (plus duckdb, lazily, for the SQL group).

Every grader returns a dict with `correct` (bool) and per-group diagnostics,
e.g. `invented_cause` or `fabricated`, so the write-up can report *how* a model
fails, not only how often.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading

GROUPS = ("tool_choice", "data_reading", "diagnosis", "sql")

# Bump when the task files start relying on something new in this module. The
# task files refuse to run against an older copy (see REQUIRED_SCORING there):
# on 25 Sept 2026 a stale dataset copy made 1,900+ calls fail with
# "has no attribute 'ask'" instead of failing once, loudly.
SCORING_VERSION = 2
TODAY = "2026-09-01"  # the fixed "today" every prompt uses, so dates are unambiguous

_STATE: dict = {}


# ── loading ──────────────────────────────────────────────────────────────────

def init(data_dir: str) -> None:
    """Point the module at the dataset folder (tools, tables, cases)."""
    _STATE.clear()
    _STATE["data_dir"] = data_dir
    with open(os.path.join(data_dir, "insighttrack_tools.json")) as fh:
        _STATE["tools"] = json.load(fh)


def load_cases(data_dir: str, group: str, limit: int = 0, difficulty: str | None = None) -> list[dict]:
    """Cases for one group; optionally only 'standard' or 'hard', optionally a small sample."""
    if group not in GROUPS:
        raise ValueError(f"unknown group {group!r}")
    init(data_dir)
    with open(os.path.join(data_dir, f"cases_{group}.jsonl")) as fh:
        cases = [json.loads(line) for line in fh if line.strip()]
    if difficulty:
        cases = [c for c in cases if c["difficulty"] == difficulty]
    if not limit or limit >= len(cases):
        return cases
    # Round-robin across subgroups, so a quick run samples every kind of case.
    buckets: dict[str, list] = {}
    for c in cases:
        buckets.setdefault(c["subgroup"], []).append(c)
    picked, i = [], 0
    while len(picked) < limit:
        for bucket in buckets.values():
            if i < len(bucket) and len(picked) < limit:
                picked.append(bucket[i])
        i += 1
    return picked


def tool_names() -> set[str]:
    return {t["name"] for t in _STATE["tools"]}


# ── calling the model ────────────────────────────────────────────────────────

# Provider errors worth retrying: overload (429), timeouts, dropped connections,
# 5xx. Matched by class name so this file needs no provider SDK imports.
_TRANSIENT = ("RateLimit", "Timeout", "APIConnection", "InternalServer", "ServiceUnavailable", "Overloaded")


def is_transient(exc: BaseException) -> bool:
    name = type(exc).__name__
    return any(t in name for t in _TRANSIENT) or getattr(exc, "status_code", None) in (429, 500, 502, 503, 504)


def call_with_retry(fn, attempts: int = 6, first_delay: float = 5.0, max_delay: float = 60.0, sleep=None):
    """Call fn(), retrying transient provider errors with exponential backoff.

    Kaggle forces max_attempts=1 inside a nested evaluate(), so without this a
    single "model is under heavy load" reply would score a case as wrong.
    Real errors (bad request, auth) are raised immediately.
    """
    import time

    sleep = sleep or time.sleep
    delay = first_delay
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — filtered by is_transient
            if attempt == attempts or not is_transient(exc):
                raise
            sleep(delay)
            delay = min(delay * 2, max_delay)


# Kaggle's model proxy prices each call up front from its MAXIMUM output, and
# refuses the call (403 "estimated cost … exceeds your available quota") when
# that worst case does not fit the remaining budget. Uncapped, one GPT-5.5 call
# was estimated at $3.84. Answers here are a few hundred tokens; 16k still
# leaves thinking models room to reason.
MAX_OUTPUT_TOKENS = 16_384


def _is_param_error(exc: BaseException) -> bool:
    """A 400 that complains about the token-limit parameter itself."""
    text = str(exc).lower()
    return (getattr(exc, "status_code", None) == 400 or "badrequest" in type(exc).__name__.lower()) and (
        "max_tokens" in text or "max_completion_tokens" in text or "unsupported parameter" in text
    )


def ask(llm, prompt: str, max_output_tokens: int = MAX_OUTPUT_TOKENS, sleep=None):
    """Prompt with a capped output length, retrying transient errors.

    Providers behind the proxy disagree on the parameter name, so try
    `max_completion_tokens`, then `max_tokens`, then no cap at all.
    """
    for params in ({"max_completion_tokens": max_output_tokens}, {"max_tokens": max_output_tokens}, None):
        try:
            if params is None:
                return call_with_retry(lambda: llm.prompt(prompt), sleep=sleep)
            return call_with_retry(lambda: llm.prompt(prompt, extra_api_params=params), sleep=sleep)
        except Exception as exc:  # noqa: BLE001
            if params is not None and _is_param_error(exc):
                continue
            raise


# ── parsing model output ─────────────────────────────────────────────────────

def extract_json(text) -> dict | None:
    """The first JSON object in a reply, tolerating code fences and prose."""
    if isinstance(text, dict):
        return text
    if not isinstance(text, str):
        return None
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidates = fenced + [text]
    for chunk in candidates:
        start = chunk.find("{")
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(chunk)):
                ch = chunk[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                elif ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(chunk[start:i + 1])
                            if isinstance(obj, dict):
                                return obj
                        except json.JSONDecodeError:
                            pass
                        break
            start = chunk.find("{", start + 1)
    return None


def extract_sql(text) -> str | None:
    if not isinstance(text, str):
        return None
    m = re.search(r"```(?:sql|duckdb)?\s*(.*?)```", text, flags=re.S | re.I)
    sql = (m.group(1) if m else text).strip()
    return sql or None


def _to_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "").rstrip("%").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


# ── group 1: tool choice ─────────────────────────────────────────────────────

def _catalogue_text() -> str:
    lines = []
    for t in _STATE["tools"]:
        params = t.get("inputSchema", {}).get("properties", {})
        required = t.get("inputSchema", {}).get("required") or []
        spec = {k: {"type": v.get("type"), **({"enum": v["enum"]} if "enum" in v else {})}
                for k, v in params.items()}
        lines.append(json.dumps({
            "name": t["name"], "description": t["description"],
            "parameters": spec, "required": required,
        }, ensure_ascii=False))
    return "\n".join(lines)


def prompt_tool_choice(case: dict) -> str:
    return f"""You are Pulse, the AI analyst inside InsightTrack, a web analytics product.
You answer questions by calling ONE of the tools below. Today is {TODAY}.

TOOLS (one JSON object per line):
{_catalogue_text()}

Rules:
- Pick the single best tool for the question.
- Include only arguments the question actually specifies.
- dateRange is one of 'today', '7d', '30d', '90d', or 'custom:YYYY-MM-DD:YYYY-MM-DD'.
- If no tool can answer the question, use "none".

User question: {case["question"]}

Reply with JSON only: {{"tool": "<tool name or none>", "arguments": {{...}}}}"""


def _norm_arg(key: str, v):
    if v is None:
        return None
    if key == "path":
        s = str(v).strip()
        return s if s.startswith("/") else "/" + s
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, (list, tuple)):
        return [_norm_arg(key, x) for x in v]
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def score_tool_choice(case: dict, response) -> dict:
    obj = extract_json(response)
    if obj is None:
        return {"correct": False, "parsed": False, "tool": None, "invalid_tool": False}
    tool = str(obj.get("tool") or "none").strip()
    args = obj.get("arguments") or {}
    if not isinstance(args, dict):
        args = {}
    invalid = tool != "none" and tool not in tool_names()
    tool_ok = tool in case["expected_tools"]
    args_ok = all(_norm_arg(k, args.get(k)) == _norm_arg(k, v) for k, v in case.get("expected_args", {}).items())
    return {
        "correct": tool_ok and args_ok,
        "parsed": True,
        "tool": tool,
        "tool_ok": tool_ok,
        "args_ok": args_ok,
        "invalid_tool": invalid,  # a tool that does not exist
    }


# ── group 2: data reading ────────────────────────────────────────────────────

def prompt_data_reading(case: dict) -> str:
    result = json.dumps(case["tool_output"], ensure_ascii=False)
    args = json.dumps(case["tool_args"], ensure_ascii=False)
    return f"""You are Pulse, the AI analyst inside InsightTrack, a web analytics product.
You called the tool `{case["tool"]}` with arguments {args} and it returned:

{result}

Question: {case["question"]}

Answer using ONLY this result. If it does not contain the information needed, answer "not_available" — do not estimate.
Give numbers without units or % signs, rounded as the question asks.

Reply with JSON only: {{"answer": <number or string>}}"""


def score_data_reading(case: dict, response) -> dict:
    obj = extract_json(response)
    if obj is None or "answer" not in obj:
        return {"correct": False, "parsed": False, "fabricated": False, "refused": False}
    given = obj["answer"]
    says_na = isinstance(given, str) and given.strip().lower().replace(" ", "_") in {"not_available", "n/a", "unknown"}
    kind = case["answer_type"]
    if kind == "unavailable":
        # Saying "not_available" here is the right answer, not a refusal.
        return {"correct": says_na, "parsed": True, "fabricated": not says_na, "refused": False}
    if says_na:
        return {"correct": False, "parsed": True, "fabricated": False, "refused": True}
    if kind == "number":
        n = _to_number(given)
        ok = n is not None and abs(n - case["answer"]) <= case.get("tolerance", 0.0) + 1e-9
    else:
        ok = str(given).strip().lower() == str(case["answer"]).strip().lower()
    return {"correct": ok, "parsed": True, "fabricated": False, "refused": False}


# ── group 3: traffic-change diagnosis ────────────────────────────────────────

DIAGNOSIS_RULES = """Decide in this order.

1. SIGNIFICANCE. Compare the last two weeks only. The change is significant only if
   BOTH |change| >= 15% of the earlier week AND |change| >= 20 views.
   If it is not significant: answer significant=false, direction=null, causes=[].
2. DIRECTION. "drop" if the last week is lower, "spike" if it is higher.
3. CAUSES. Check every keyword. List each code whose condition holds for AT LEAST ONE
   keyword (each code once). "any" codes count in either direction.
   The site is "quoted" when its domain (or a subdomain) is in the AI answer's quotes.
   - rank_drop (any): ranked both times and the position got worse by 3 or more places.
   - page_one_exit (any): position 1-10 before; now below 10 or not ranking at all.
   - ai_overview_displacement (any): no AI answer before, an AI answer now, and it does not quote the site.
   - ai_citation_lost (any): the site was quoted before and is not quoted now.
   - serp_feature_added (drop only): the site is in positions 1-10 now, and one of these blocks
     appeared that was not there before: featured_snippet, people_also_ask, videos, shopping, knowledge_graph.
   - serp_feature_removed (spike only): the site is in positions 1-10 now, and one of those blocks disappeared.
   - rank_gain (spike only): ranked both times and the position improved by 3 or more places.
   - ai_citation_gained (spike only): an AI answer was shown before without quoting the site, and now it quotes the site.
   - unexplained_by_serp: the change is significant but none of the codes above applies.
   Moves of 1-2 places are normal jitter and are never a cause. Position null means not ranking."""


def prompt_diagnosis(case: dict) -> str:
    evidence = {
        "site_domain": case["domain"],
        "weekly_pageviews_oldest_first": case["weeks"],
        "keywords": [
            {"keyword": k["keyword"], "google_before": k["before"], "google_after": k["after"]}
            for k in case["keywords"]
        ],
    }
    return f"""You are Pulse, the AI analyst inside InsightTrack, a web analytics product.
A user asks why traffic to one of their pages changed. You have the page's weekly
pageviews (complete weeks, oldest first) and, for each keyword the page targets, two
Google snapshots: one from before the last week and one from now.

{DIAGNOSIS_RULES}

Evidence:
{json.dumps(evidence, ensure_ascii=False, indent=1)}

Reply with JSON only:
{{"significant": true|false, "direction": "drop"|"spike"|null, "causes": ["code", ...]}}"""


def score_diagnosis(case: dict, response) -> dict:
    gold = case["gold"]
    obj = extract_json(response)
    if obj is None:
        return {"correct": False, "parsed": False, "invented_cause": False, "missed_significance": False}
    sig = obj.get("significant")
    if isinstance(sig, str):
        sig = sig.strip().lower() == "true"
    causes = obj.get("causes") or []
    if not isinstance(causes, list):
        causes = [causes]
    causes = sorted({str(c).strip() for c in causes if str(c).strip()})
    direction = obj.get("direction")
    direction = str(direction).strip().lower() if direction not in (None, "", "null") else None

    serp = [c for c in causes if c != "unexplained_by_serp"]
    gold_serp = [c for c in gold["causes"] if c != "unexplained_by_serp"]
    if not gold["significant"]:
        correct = sig is False
    else:
        correct = sig is True and direction == gold["direction"] and causes == gold["causes"]
    return {
        "correct": bool(correct),
        "parsed": True,
        # Blamed search when the right answer had no search cause at all.
        "invented_cause": bool(serp) and not gold_serp,
        # Called a real, significant change noise (or the reverse).
        "missed_significance": sig is not gold["significant"],
    }


# ── group 4: SQL ─────────────────────────────────────────────────────────────

SQL_SCHEMA = """CREATE TABLE events (
  id VARCHAR, site_id VARCHAR NOT NULL, user_id VARCHAR NOT NULL,
  session_id VARCHAR NOT NULL, type VARCHAR NOT NULL, url VARCHAR,
  path VARCHAR, referrer VARCHAR, device VARCHAR, browser VARCHAR,
  os VARCHAR, country VARCHAR, city VARCHAR, timestamp TIMESTAMP NOT NULL,
  properties VARCHAR, utm_source VARCHAR, utm_medium VARCHAR,
  utm_campaign VARCHAR, utm_term VARCHAR, utm_content VARCHAR
);

CREATE TABLE sessions (
  id VARCHAR PRIMARY KEY, site_id VARCHAR NOT NULL, user_id VARCHAR NOT NULL,
  started_at TIMESTAMP NOT NULL, ended_at TIMESTAMP NOT NULL,
  duration INTEGER DEFAULT 0, pageviews SMALLINT DEFAULT 1,
  entry_page VARCHAR, exit_page VARCHAR, referrer VARCHAR,
  device VARCHAR, browser VARCHAR, os VARCHAR, country VARCHAR,
  is_bounce BOOLEAN DEFAULT FALSE, is_returning BOOLEAN DEFAULT FALSE,
  utm_source VARCHAR, utm_medium VARCHAR, utm_campaign VARCHAR
);"""

SQL_NOTES = """Data notes:
- One site. events.type is 'pageview' or 'custom'; custom events keep their name in
  properties as JSON, e.g. '{"name": "signup"}'.
- device is 'desktop', 'mobile' or 'tablet'. country is an ISO code such as 'IN' or 'US'.
- referrer is a full URL, or '' for direct visits. timestamps are UTC.
- sessions.duration is in seconds; is_bounce is true for single-page sessions.
- "Between dates A and B" means both days included, compared on the calendar date."""


def prompt_sql(case: dict) -> str:
    return f"""You are Pulse, the AI analyst inside InsightTrack, a web analytics product.
Write ONE DuckDB SQL query that answers the question over these tables:

{SQL_SCHEMA}

{SQL_NOTES}

Question: {case["question"]}

Return exactly the columns the question asks for, in that order. Reply with the query only, in a ```sql block."""


_SQL_TIMEOUT_S = 15
_SQL_LOCK = threading.Lock()


def _connection():
    if "db" in _STATE:
        return _STATE["db"]
    import duckdb  # lazy: only the SQL group needs it

    con = duckdb.connect(":memory:")
    for table in ("events", "sessions"):
        path = os.path.join(_STATE["data_dir"], f"{table}.parquet")
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{path}')")
    # After loading, the model's SQL can reach nothing outside these tables.
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")
    _STATE["db"] = con
    return con


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|export|import|install|load|pragma|set|call|checkpoint|vacuum)\b",
    re.I,
)


def check_sql(sql: str | None) -> str | None:
    """Reason the query may not run, or None when it is a single read-only SELECT."""
    if not sql:
        return "empty"
    body = sql.strip().rstrip(";").strip()
    if ";" in body:
        return "multiple statements"
    if not re.match(r"^(select|with)\b", body, re.I):
        return "not a SELECT"
    stripped = re.sub(r"'(?:[^']|'')*'", "''", body)  # ignore words inside string literals
    if _FORBIDDEN.search(stripped):
        return "forbidden statement"
    return None


def run_sql(sql: str) -> list[tuple]:
    """Execute read-only SQL with a timeout; raises on error."""
    problem = check_sql(sql)
    if problem:
        raise ValueError(problem)
    con = _connection()
    with _SQL_LOCK:
        cur = con.cursor()
        timer = threading.Timer(_SQL_TIMEOUT_S, cur.interrupt)
        timer.start()
        try:
            return cur.execute(sql.strip().rstrip(";")).fetchall()
        finally:
            timer.cancel()
            cur.close()


def _norm_cell(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if hasattr(v, "isoformat"):
        # A DATE, or a TIMESTAMP at midnight, both compare as the plain day.
        if type(v).__name__ == "date" or (hasattr(v, "hour") and not (v.hour or v.minute or v.second or v.microsecond)):
            return v.isoformat()[:10]
        return v.isoformat()
    n = _to_number(v) if not isinstance(v, str) else None
    if n is not None:
        return round(n, 1)
    if hasattr(v, "__float__") and not isinstance(v, str):
        return round(float(v), 1)
    return str(v).strip()


def _cells_equal(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= 0.051
    return a == b


def rows_equal(actual: list, expected: list, ordered: bool) -> bool:
    act = [[_norm_cell(c) for c in row] for row in actual]
    exp = [[_norm_cell(c) for c in row] for row in expected]
    if len(act) != len(exp) or any(len(a) != len(e) for a, e in zip(act, exp)):
        return False
    if not ordered:
        key = lambda r: json.dumps(r, default=str)
        act, exp = sorted(act, key=key), sorted(exp, key=key)
    return all(_cells_equal(a, e) for ra, re_ in zip(act, exp) for a, e in zip(ra, re_))


def score_sql(case: dict, response) -> dict:
    sql = extract_sql(response)
    problem = check_sql(sql)
    if problem:
        return {"correct": False, "parsed": sql is not None, "executed": False, "error": problem}
    try:
        rows = run_sql(sql)
    except Exception as exc:  # the model's SQL failed to run
        return {"correct": False, "parsed": True, "executed": False, "error": type(exc).__name__}
    return {
        "correct": rows_equal(rows, case["expected"], case["ordered"]),
        "parsed": True,
        "executed": True,
        "error": None,
    }


# ── dispatch + aggregation ───────────────────────────────────────────────────

PROMPTS = {
    "tool_choice": prompt_tool_choice,
    "data_reading": prompt_data_reading,
    "diagnosis": prompt_diagnosis,
    "sql": prompt_sql,
}
SCORERS = {
    "tool_choice": score_tool_choice,
    "data_reading": score_data_reading,
    "diagnosis": score_diagnosis,
    "sql": score_sql,
}


def build_prompt(case: dict) -> str:
    return PROMPTS[case["group"]](case)


def score(case: dict, response) -> dict:
    out = SCORERS[case["group"]](case, response)
    out.update({"id": case["id"], "subgroup": case["subgroup"], "difficulty": case["difficulty"]})
    return out


def aggregate(results: list[dict], total: int) -> tuple[float, float]:
    """(accuracy, standard error) over ALL cases; a failed run counts as wrong."""
    correct = sum(1 for r in results if isinstance(r, dict) and r.get("correct"))
    if total <= 0:
        return 0.0, 0.0
    p = correct / total
    return float(p), float(math.sqrt(p * (1 - p) / total))


def breakdown(results: list[dict]) -> dict:
    """Accuracy per subgroup plus the failure-mode counters, for the write-up."""
    out: dict = {}
    for r in results:
        if not isinstance(r, dict):
            continue
        tier = out.setdefault("TIER " + r.get("difficulty", "?"), {"n": 0, "correct": 0})
        tier["n"] += 1
        tier["correct"] += int(bool(r.get("correct")))
        g = out.setdefault(r.get("subgroup", "?"), {"n": 0, "correct": 0})
        g["n"] += 1
        g["correct"] += int(bool(r.get("correct")))
        for flag in ("invented_cause", "fabricated", "invalid_tool", "missed_significance", "refused"):
            if r.get(flag):
                g[flag] = g.get(flag, 0) + 1
    return out
