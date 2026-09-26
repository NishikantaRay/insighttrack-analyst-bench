# InsightTrack Analyst Bench

**Which LLM should power InsightTrack's AI analyst?** This benchmark answers
that by giving models the job Pulse does inside
[InsightTrack](https://github.com/NishikantaRay/InsightTrack), an open-source web
analytics platform, and grading the answers automatically.

Built for the DEV × Kaggle Benchmarking Challenge (tags: `devchallenge`, `kagglechallenge`).

**New here? Start with [docs/step-by-step.md](docs/step-by-step.md).** All docs: [docs/index.md](docs/index.md).

## What it measures

480 cases in four groups of 120: **80 standard + 40 hard** each. Each group is its
own Kaggle task, and the four together form the benchmark. Every case is labelled
`standard` or `hard`, and the tasks report both tiers.

| Group | The model gets | Graded on | Failure it exposes |
|---|---|---|---|
| **Tool choice** | A user question and InsightTrack's real 23-tool Pulse catalogue | Right tool and right arguments (`dateRange`, `path`, `keyword`, `limit`) | Calling a tool that doesn't exist; using the nearest tool when the right answer is "none" |
| **Data reading** | A tool result in InsightTrack's real output format, plus a question | The number or path, within a stated tolerance | Inventing a number when the data doesn't contain it (39 of 120 cases) |
| **Diagnosis** | 8 weeks of page traffic, plus Google results before and after | Whether the change is real, its direction, and the **exact** set of causes | Blaming search for noise, or for a change search didn't cause |
| **SQL** | InsightTrack's DuckDB `events` / `sessions` tables and a question | The *result* of running the query, not its text | Queries that run but answer a different question |

Accuracy counts every case: a run that never completes counts as wrong. Each
grader also records how a model fails (`invented_cause`, `fabricated`,
`invalid_tool`, `missed_significance`, `refused`), and the tasks print a
per-subgroup breakdown.

### Standard subgroups (80 per group)

- **Tool choice**: 58 direct, 17 near-miss (two tools sound plausible), 5 with no suitable tool. When two tools are both defensible, both are accepted.
- **Data reading**: 44 numeric, 12 "which page", 24 unanswerable.
- **Diagnosis**:
  - 20 single-cause cases
  - 16 multi-cause cases
  - 16 unexplained: traffic moved but search didn't change
  - 16 not significant: a huge % on tiny numbers, or a small % on big ones, while search *did* change
  - 12 decoys: a real move plus a search change that isn't a cause, such as a 2-place jitter, a new block below page one, a rank gain during a drop, or a new AI answer that quotes the site
- **SQL**: 12 question types, such as top pages, bounce rate by device, custom events from JSON properties, search share, daily series and most common exit page.

### Hard subgroups (40 per group)

The standard tier is easy for frontier models. The hard tier is built to separate them.

- **Tool choice**:
  - dates relative to "today", such as "yesterday" → `custom:2026-08-31:2026-08-31`
  - three arguments at once (keyword + device + location)
  - a site named in the question, where the registry says to call `list_sites` first
  - a release-regression question that tempts the JS-errors tool
  - 8 requests no tool can serve, such as revenue, ads or exports
- **Data reading**:
  - exact shares, where the rounded `percentage` field fails the tolerance
  - converting "3m 25s" to seconds
  - the previous period's pages per visitor, worked back from two trends
  - yes/no trend comparisons and medians
  - traps that *look* answerable, such as unique visitors summed across pages (the same people counted twice), a site total from a top-10 list, or a sources × device cross-tab
- **Diagnosis**:
  - several keywords pulling in different directions
  - every threshold hit exactly (15% and 20 views, a 3-place move, positions 10 ↔ 11)
  - subdomain and `www.` quotes that count, and lookalike domains that don't
  - "not ranking" transitions (7 → none, 15 → none, none → 6)
  - "any" causes that still count when traffic *rose*
  - each hard builder states its intended answer, and the build fails if the rules disagree
- **SQL**:
  - joins between `events` and `sessions`
  - `LAG` windows
  - page A then page B in the same session
  - users active on N or more days
  - `MEDIAN`, and a `CASE` channel mapping

## What comes from InsightTrack

Nothing here needs InsightTrack running. The pieces below are copied or ported
from it, and two tests check they still match the product.

| Benchmark piece | Source in InsightTrack | Kept in sync by |
|---|---|---|
| `insighttrack_bench/rules.py`: significance, cause rules, citation and feature comparison | `analytics-api/src/services/correlationService.js`, and the derivation in `searchVisibilityService.checkKeyword()` | `tests/test_parity.py` runs the **original JavaScript** on all 120 cases plus 1,500 random ones (1–3 keywords each) |
| `data/insighttrack_tools.json`: the 23 Pulse tools | `toolCatalogue()` in `analytics-api/src/mcp/tools/registry.js` | `tests/test_tasks_and_tools.py` compares it with the live registry |
| `SQL_SCHEMA` in `scoring.py` | `events` and `sessions` in `analytics-api/src/schema/schema.js` | Copied as-is |
| Data-reading output formats | `getTrafficSources`, `getDeviceBreakdown`, `getTopPages`, `getKPISummary` in `queries.js` | Same field names, in the `{summary, data}` wrapper Pulse sees |

`daily_stats` is left out of the SQL group on purpose. InsightTrack's rollup
writes `bounces = 0`, so questions over it would have no fair answer.

## Layout

```
insighttrack_bench/     builds the dataset (runs locally, not uploaded)
  rules.py              answer key for diagnosis (port of correlationService.js)
  scoring.py            prompts + graders; shipped to Kaggle as itbench_scoring.py
  gen_tool_choice.py    group 1 cases
  gen_data_reading.py   group 2 cases
  gen_diagnosis.py      group 3 cases (gold always from rules.py, then checked)
  gen_sql.py            group 4 sample tables + cases (gold = running the reference SQL)
  build.py              writes dataset/
tasks/                  one Kaggle task file per group
dataset/                the Kaggle dataset (generated; safe to delete and rebuild)
data/insighttrack_tools.json
scripts/parity.mjs      runs InsightTrack's JS engine for the parity test
scripts/export_tools.mjs  re-exports the tool catalogue from InsightTrack
docs/                   guides: step-by-step, how it works, task groups, testing, troubleshooting, the post
tests/                  91 tests
smoke_test.py           one-question check that the Kaggle loop works
```

## Setup

```bash
cd ~/Desktop/Personal/kaggle-bench
export PATH="$PWD/.venv/bin:$PATH"          # use this project's Python and kaggle CLI
export KAGGLE_API_TOKEN=...                 # from kaggle.com → Settings → API
```

To set up from scratch instead:
```bash
uv venv --python 3.12 && uv pip install -r requirements.txt
```

## Build and test (no model calls)

```bash
python -m insighttrack_bench.build --owner <your-kaggle-username>   # writes dataset/
python -m pytest                                                     # 91 tests
```

The build is seeded, so a rebuild is byte-for-byte identical. The tests check that:
- a perfect model scores 100% in every group, and garbage scores 0; each group has 80 standard + 40 hard cases
- every diagnosis answer can be recomputed, and matches InsightTrack's JavaScript
- every reference query reproduces its stored answer on the shipped tables
- unsafe SQL is refused, and the model's SQL cannot read files or change the tables
- each failure-mode flag fires when it should
- the task files match their Kaggle task names

The parity and tool-sync tests need Node and a local InsightTrack checkout
(`INSIGHTTRACK_API=<path>/apps/analytics-api`). Without them, those tests skip.

## Run locally against a model

```bash
kaggle b init -y                          # writes .env (short-lived model login, model list)
python smoke_test.py                      # 1 question
ITBENCH_LIMIT=5 ITBENCH_MODEL=anthropic/claude-sonnet-5@default \
  python tasks/diagnosis.py               # 5 cases, one of each kind, on a chosen model
```

Locally you only get the small set of models listed in `.env`. The full model list is available on Kaggle.

## Publish on Kaggle

```bash
# 1. Upload the dataset (first time: create; after changes: version)
kaggle datasets create -p dataset -t          # -t keeps .parquet files as they are
kaggle datasets version -p dataset -t -m "rebuild"

# 2. Push each group as a task, with the dataset attached
for g in tool_choice data_reading diagnosis sql; do
  kaggle b t push insighttrack_$g -f tasks/$g.py -d <you>/insighttrack-analyst-bench --wait
done

# 3. Run them against models
kaggle b t run insighttrack_diagnosis -m <model> -m <model> --wait
kaggle b t status insighttrack_diagnosis
kaggle b t download insighttrack_diagnosis -o runs/

# 4. Make the tasks public, then group the four into one benchmark on kaggle.com
kaggle b t publish insighttrack_diagnosis
```

Notes:
- Re-pushing without `-d` detaches the dataset. Pass it every time.
- `evaluate()` retries failed calls and caches finished ones, so a rerun only redoes what failed.
- Model use has a budget. Test with `ITBENCH_LIMIT` before running all 120 cases per group on every model. Claude Sonnet 5 cost about $0.004 per case, so about $2 for all 480.

## Fairness notes

- **"Correct" means correct by InsightTrack's documented rules.** The diagnosis prompt states every rule and threshold (15% **and** 20 views, a 3-place move, page one = #1–10, which blocks count), so the task tests careful application, not guessing a hidden convention.
- **All prompts are plain text asking for JSON**, and the grader tolerates code fences and surrounding prose. Kaggle only supports automatic tool calling for Gemini, so native tool use would not be fair across providers.
- **All data is synthetic.** No real site's traffic is used.

## Credits

- Rules, tool catalogue and schema: [InsightTrack](https://github.com/NishikantaRay/InsightTrack) (the author's own project).
- Evaluation harness: [Kaggle Benchmarks](https://github.com/Kaggle/kaggle-benchmarks). The task pattern follows its `dataset_evaluation.py` example.
- Related benchmarks that each cover one slice of this: BFCL and τ-bench (tool calling), InfiAgent-DABench and DSBench (data analysis), Spider 2.0 and BIRD (text-to-SQL). This benchmark differs by testing one real product's job end to end, and by scoring whether a model knows when nothing happened.
