"""Build the Kaggle dataset folder.

    python -m insighttrack_bench.build [--out dataset] [--owner <kaggle-username>]

Writes, into --out:
  cases_<group>.jsonl        the test cases with their gold answers
  events.parquet, sessions.parquet   sample tables for the SQL group
  insighttrack_tools.json    InsightTrack's Pulse tool catalogue
  itbench_scoring.py         prompts + graders (copy of scoring.py)
  manifest.json              counts, seeds and subgroup sizes
  dataset-metadata.json      for `kaggle datasets create/version`

Everything is seeded, so a rebuild is byte-for-byte reproducible.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import Counter

from . import gen_data_reading, gen_diagnosis, gen_sql, gen_tool_choice

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS = {"tool_choice": 11, "data_reading": 13, "diagnosis": 7, "sql_tables": 17, "sql": 19}
DATASET_SLUG = "insighttrack-analyst-bench"


def _write_jsonl(path, rows):
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def build(out: str, owner: str) -> dict:
    os.makedirs(out, exist_ok=True)

    events, sessions = gen_sql.build_tables(SEEDS["sql_tables"])
    con = gen_sql.load_into_duckdb(events, sessions)
    for table in ("events", "sessions"):
        # ORDER BY keeps the parquet files reproducible across rebuilds.
        con.execute(f"COPY (SELECT * FROM {table} ORDER BY id) TO '{os.path.join(out, table + '.parquet')}' (FORMAT PARQUET)")

    groups = {
        "tool_choice": gen_tool_choice.build(SEEDS["tool_choice"]),
        "data_reading": gen_data_reading.build(SEEDS["data_reading"]),
        "diagnosis": gen_diagnosis.build(SEEDS["diagnosis"]),
        "sql": gen_sql.build(con, SEEDS["sql"]),
    }
    for name, cases in groups.items():
        _write_jsonl(os.path.join(out, f"cases_{name}.jsonl"), cases)

    shutil.copy(os.path.join(ROOT, "data", "insighttrack_tools.json"), os.path.join(out, "insighttrack_tools.json"))
    shutil.copy(os.path.join(ROOT, "insighttrack_bench", "scoring.py"), os.path.join(out, "itbench_scoring.py"))

    manifest = {
        "seeds": SEEDS,
        "tables": {"events": len(events), "sessions": len(sessions)},
        "groups": {name: {"cases": len(c),
                          "difficulty": dict(sorted(Counter(x["difficulty"] for x in c).items())),
                          "subgroups": dict(sorted(Counter(x["subgroup"] for x in c).items()))}
                   for name, c in groups.items()},
    }
    with open(os.path.join(out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(out, "dataset-metadata.json"), "w") as fh:
        json.dump(dataset_metadata(owner, manifest), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return manifest


TITLE = "InsightTrack Analyst Bench"  # 6-50 chars (Kaggle rule)
SUBTITLE = "480 cases testing LLMs as the AI analyst in a web analytics product"  # 20-80 chars
# Must be existing Kaggle tags: one unknown tag makes Kaggle reject the WHOLE metadata
# update (seen with "llm" on 25 Sept 2026), file descriptions included.
KEYWORDS = ["benchmark", "nlp", "sql", "internet", "websites", "data analytics"]

FILE_DESCRIPTIONS = {
    "cases_tool_choice.jsonl": "Group 1: a user question; the model must pick the right InsightTrack tool and arguments, or \"none\". 120 cases (80 standard, 40 hard).",
    "cases_data_reading.jsonl": "Group 2: a tool result in InsightTrack's real output format plus a question; 39 of 120 cannot be answered from the data.",
    "cases_diagnosis.jsonl": "Group 3: weekly page traffic plus Google results before and after; is the change real, and what caused it? Gold answers come from InsightTrack's own correlation rules.",
    "cases_sql.jsonl": "Group 4: a question over the events/sessions tables with a reference query and its result. Model SQL is executed and graded on its output.",
    "events.parquet": "Synthetic tracking events (pageviews and custom events), July-August 2026, in InsightTrack's DuckDB `events` layout.",
    "sessions.parquet": "Synthetic sessions for the same period, in InsightTrack's DuckDB `sessions` layout.",
    "insighttrack_tools.json": "InsightTrack's 23 Pulse tools (name, description, JSON Schema), exported from the product's tool registry.",
    "itbench_scoring.py": "Prompts and graders used by the Kaggle tasks (standard library only; DuckDB for the SQL group).",
    "manifest.json": "Seeds, table sizes and case counts per group, difficulty and subgroup.",
}


def dataset_description(manifest: dict) -> str:
    g = manifest["groups"]
    return f"""**Which LLM should power the AI analyst inside a real analytics product?** This dataset holds
the cases, sample tables and graders for **InsightTrack Analyst Bench**, a Kaggle benchmark that gives models
the job of *Pulse*, the AI analyst in [InsightTrack](https://github.com/NishikantaRay/InsightTrack), an
open-source web analytics platform.

### Four task groups, {sum(v["cases"] for v in g.values())} cases

| Group | The model gets | Graded on |
|---|---|---|
| Tool choice ({g["tool_choice"]["cases"]}) | A user question and the real 23-tool Pulse catalogue | Right tool and arguments, or "none" |
| Data reading ({g["data_reading"]["cases"]}) | A real-shaped tool result and a question | The number or path; "not_available" when the data lacks it |
| Diagnosis ({g["diagnosis"]["cases"]}) | Weekly traffic plus Google results before and after | Real change or noise, direction, and the exact causes |
| SQL ({g["sql"]["cases"]}) | The DuckDB events/sessions tables and a question | The query's result, run read-only |

Each group has **80 standard + 40 hard** cases. Graders also label *how* a model fails: invented causes,
made-up numbers, tools that don't exist, noise called real (or the reverse).

### How the answers are known
- **Diagnosis:** a Python port of InsightTrack's `correlationService.js`, checked against the original JavaScript on every case and 1,500 random ones.
- **SQL:** each reference query is run on the shipped tables.
- **Data reading:** computed from the same data the model sees.
- **Tool choice:** each question names the tool(s) that answer it; both are accepted when two are defensible.

### Notes
- All data is **synthetic**; no real site's visitors are included.
- Everything is seeded and rebuilds byte-for-byte.
- Built for the DEV x Kaggle Benchmarking Challenge.
- Source, tests and docs: the `kaggle-bench` project alongside InsightTrack.
"""


# Column descriptions for the parquet tables. Kaggle needs ALL columns, in order.
_EVENTS_COLUMNS = [
    ("id", "string", "Event id"), ("site_id", "string", "Site the event belongs to (one site: site_demo)"),
    ("user_id", "string", "Anonymous visitor id"), ("session_id", "string", "Session id; joins sessions.id"),
    ("type", "string", "'pageview' or 'custom'"), ("url", "string", "Full page URL"),
    ("path", "string", "Page path, e.g. /pricing"), ("referrer", "string", "Referrer URL, or '' for direct"),
    ("device", "string", "desktop, mobile or tablet"), ("browser", "string", "Browser name"),
    ("os", "string", "Operating system"), ("country", "string", "ISO country code, e.g. IN"),
    ("city", "string", "City name"), ("timestamp", "datetime", "Event time (UTC)"),
    ("properties", "string", "JSON for custom events, e.g. {\"name\": \"signup\"}; null for pageviews"),
    ("utm_source", "string", "UTM source"), ("utm_medium", "string", "UTM medium"),
    ("utm_campaign", "string", "UTM campaign"), ("utm_term", "string", "UTM term (unused)"),
    ("utm_content", "string", "UTM content (unused)"),
]
_SESSIONS_COLUMNS = [
    ("id", "string", "Session id"), ("site_id", "string", "Site id (site_demo)"),
    ("user_id", "string", "Anonymous visitor id"), ("started_at", "datetime", "First event time (UTC)"),
    ("ended_at", "datetime", "Last event time (UTC)"), ("duration", "integer", "Seconds between first and last event"),
    ("pageviews", "integer", "Pageviews in the session"), ("entry_page", "string", "First page path"),
    ("exit_page", "string", "Last page path"), ("referrer", "string", "Referrer URL, or '' for direct"),
    ("device", "string", "desktop, mobile or tablet"), ("browser", "string", "Browser name"),
    ("os", "string", "Operating system"), ("country", "string", "ISO country code"),
    ("is_bounce", "boolean", "True for single-page sessions"),
    ("is_returning", "boolean", "True if the visitor had an earlier session"),
    ("utm_source", "string", "UTM source"), ("utm_medium", "string", "UTM medium"),
    ("utm_campaign", "string", "UTM campaign"),
]


def _resource(path: str, text: str) -> dict:
    res = {"path": path, "description": text}
    columns = {"events.parquet": _EVENTS_COLUMNS, "sessions.parquet": _SESSIONS_COLUMNS}.get(path)
    if columns:
        res["schema"] = {"fields": [{"name": n, "type": t, "description": d} for n, t, d in columns]}
    return res


def dataset_metadata(owner: str, manifest: dict) -> dict:
    return {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "description": dataset_description(manifest),
        "id": f"{owner}/{DATASET_SLUG}",
        "licenses": [{"name": "CC0-1.0"}],
        "keywords": KEYWORDS,
        "expectedUpdateFrequency": "never",
        "userSpecifiedSources": ("Synthetic, generated by the InsightTrack Analyst Bench builder. Diagnosis rules ported "
                                 "from InsightTrack's correlationService.js; tool catalogue and table layouts from "
                                 "[InsightTrack](https://github.com/NishikantaRay/InsightTrack)."),
        "resources": [_resource(path, text) for path, text in FILE_DESCRIPTIONS.items()],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "dataset"))
    ap.add_argument("--owner", default=os.environ.get("KAGGLE_USERNAME", "YOUR_KAGGLE_USERNAME"))
    args = ap.parse_args()
    manifest = build(args.out, args.owner)
    print(json.dumps(manifest["groups"], indent=2))
    print(f"tables: {manifest['tables']}  ->  {args.out}")


if __name__ == "__main__":
    main()
