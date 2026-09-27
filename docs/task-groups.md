# The four task groups

Each section shows a real case from `dataset/`, the correct answer, and how it's
graded. See the full prompt for any case with:

```bash
python -c "import json,sys; sys.path.insert(0,'insighttrack_bench'); import scoring as s; s.init('dataset'); \
c=[json.loads(l) for l in open('dataset/cases_diagnosis.jsonl')][0]; print(s.build_prompt(c))"
```

---

Every group has **80 standard + 40 hard** cases. Hard subgroups start with `hard_`, and
the README lists them. Run only one tier locally with `ITBENCH_DIFFICULTY=hard`.

## 1. Tool choice (`tasks/tool_choice.py`)

**Question:** can the model pick the right Pulse tool, with the right arguments?

**Example** (`tool_001`):

> *How is my site doing today?*

- **Correct:** `{"tool": "get_kpi", "arguments": {"dateRange": "today"}}`
- **The model sees** all 23 tools with their descriptions and parameters, and must reply with JSON.
- **Graded:**
  - The tool must be one of `expected_tools`.
  - Every argument the question states must match. Paths are compared with or without a leading `/`, and other text ignores case.
  - Arguments the question doesn't mention are ignored.

| Subgroup | Count | What it checks |
|---|---|---|
| direct | 58 | One clear tool |
| near_miss | 17 | Two tools sound plausible. When both are defensible, both are accepted. |
| no_tool | 5 | No tool can do it (e.g. "delete my site"). The answer must be `"none"`. |

**Flag:** `invalid_tool`, meaning the model named a tool that doesn't exist.

---

## 2. Data reading (`tasks/data_reading.py`)

**Question:** given a real-shaped tool result, does the model get the number right, and admit when the data can't answer?

**Example** (`read_002`): the model is shown this `get_sources` result:

```json
{"summary": "Top source was Search with 2,665 visitors.",
 "data": [{"source": "Search", "visitors": 2665, "percentage": 40},
          {"source": "Email", "visitors": 2216, "percentage": 34},
          {"source": "Direct", "visitors": 807, "percentage": 12},
          {"source": "Social", "visitors": 573, "percentage": 9},
          {"source": "Referral", "visitors": 330, "percentage": 5}]}
```

> *What percentage of visitors came from Direct or Social combined? Round to 1 decimal place.*

- **Correct:** `20.9`, from (807 + 573) / 6,591.
- **Tolerance:** ±1.0, so adding the rounded percentages (12 + 9 = 21) also passes.

| Subgroup | Count | What it checks |
|---|---|---|
| number | 44 | Arithmetic on the data (differences, shares, ratios, the previous period from a trend %) |
| text | 12 | Which page (e.g. most views per visitor) |
| unavailable | 24 | The data doesn't contain the answer (e.g. bounce rate from a sources table). Correct is `"not_available"`. |

**Flags:**
- `fabricated`: gave a number when the answer was unavailable.
- `refused`: said "not_available" when the answer was there.

---

## 3. Diagnosis (`tasks/diagnosis.py`), the headline group

**Question:** traffic moved. Is it real, and did search cause it?

**The model sees:** 8 weeks of pageviews, Google results for the page's keyword before and after, and every rule written out (below).

**Decoy example** (`diag_069`):
- **Traffic:** `… 517, 347`, a 33% drop of 170 views, so it's real.
- **Google:** position `#3 → #5`, nothing else changed.
- **Correct:** `{"significant": true, "direction": "drop", "causes": ["unexplained_by_serp"]}`.
- **Why:** a 2-place move is jitter, so search didn't cause this. A model that answers `rank_drop` gets it wrong and is flagged `invented_cause`.

**Not-significant example** (`diag_053`):
- **Traffic:** `1970 → 2017`, only +2.4%.
- **Google:** meanwhile the rank fell `#5 → #10`, an AI answer appeared, and a knowledge panel was added.
- **Correct:** `{"significant": false, "direction": null, "causes": []}`. The traffic didn't really move, however dramatic search looks.

**The rules** (also in the prompt):
- Significant only if the change is ≥ 15% **and** ≥ 20 views.
- Causes: `rank_drop`, `page_one_exit`, `ai_overview_displacement`, `ai_citation_lost`, `serp_feature_added` (drop only, on page one), `serp_feature_removed` / `rank_gain` / `ai_citation_gained` (spike only), and `unexplained_by_serp`.
- A move of 1–2 places is never a cause.

> **Known issue (task v4):** the prompt line "Moves of 1-2 places are normal jitter and are never a cause"
> clashes with `page_one_exit` when a page moves from #10 to #11. GPT-5.5 read it literally and missed exactly
> those cases (4 of 120). The fix for the next version: "never counts as rank_drop or rank_gain". Changing it means
> a new task version and rerunning every model, because the leaderboard only shows the newest version.

**Graded:**
- **Not significant:** the model must say `significant: false`.
- **Significant:** it must match significant, direction and the **exact** set of causes. Order doesn't matter.

| Subgroup | Count | What it checks |
|---|---|---|
| single_cause | 20 | One cause; every code appears at least once |
| multi_cause | 16 | Two or three causes at once |
| unexplained | 16 | Traffic moved, and search looks quiet |
| not_significant | 16 | Traffic didn't really move, and search changed anyway |
| decoy | 12 | A real move plus a search change that doesn't count: 2-place jitter, a new block below page one, a rank *gain* during a drop, or a new AI answer that quotes the site |

**Flags:**
- `invented_cause`: blamed search when the correct answer had no search cause.
- `missed_significance`: called noise real, or real change noise.

---

## 4. SQL (`tasks/sql.py`)

**Question:** can the model write DuckDB SQL that returns the right answer from InsightTrack's tables?

**Example** (`sql_003`):

> *List the top 3 pages by pageviews between 2026-07-26 and 2026-08-03, most viewed first; break ties by path A→Z. Return columns: path, pageviews.*

- **Correct result:** `/blog/acid-properties-explained 143`, `/ 130`, `/blog/sql-joins-visual-guide 112`.
- **The model sees** the `events` and `sessions` tables, a few notes about the data, and the question.
- **Graded:**
  - The query must be a single `SELECT` or `WITH`.
  - It runs read-only, with a 15-second limit, on the sample tables (5,940 events, 2,494 sessions, July–August 2026). It can't read files or change tables.
  - Its rows must match. Order is checked only when the question asks for it, and numbers can be off by up to 0.05.

**Standard question types** (80 cases, 4 to 7 each): top pages, pageviews for a page, unique visitors on a day, bounce rate by device, top countries, average duration by entry page, sessions from a UTM source, a page's daily series, counts of a named custom event (inside JSON), search-engine share, returning sessions by device, and most common exit page.
