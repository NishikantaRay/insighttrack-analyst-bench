# How it works

## The idea

InsightTrack has an AI analyst, **Pulse**, that answers questions about a
website's traffic. Something has to power it. This benchmark gives each model
Pulse's job and checks the answers against known-correct results, so choosing
the model becomes a measured decision instead of a guess.

## From a case to a score

```
insighttrack_bench/  (on your Mac)                 Kaggle
────────────────────────────────                   ─────────────────────────────
gen_*.py  ──►  cases + correct answers  ──┐
rules.py  ──►  (diagnosis answer key)     ├──►  dataset/  ──upload──►  dataset
gen_sql.py ─►  sample tables (parquet)    │                             │
scoring.py ─────────── copied as ─────────┘                             ▼
                        itbench_scoring.py                     tasks/<group>.py
                                                               for each case:
                                                                 prompt = build_prompt(case)
                                                                 reply  = model(prompt)
                                                                 result = score(case, reply)
                                                               → accuracy for this model
```

1. **Generate.** Each `gen_*.py` makes 80 standard + 40 hard cases with a fixed random seed, so a rebuild gives identical files.
2. **Work out the correct answer.** Each group gets its answer differently:
   - **Diagnosis:** InsightTrack's own rules (`rules.py`).
   - **SQL:** run the reference query on the sample tables.
   - **Data reading:** calculate it from the data shown to the model.
   - **Tool choice:** written into each question's template.
3. **Package.** `build.py` writes everything to `dataset/`, including the scoring code, so Kaggle grades with exactly the code that was tested.
4. **Ask.** On Kaggle, each task file sends every case's prompt to the model.
5. **Retry busy models.** If a provider answers "heavy load" (429), a timeout or a 5xx, the call is retried with growing waits, for about 2 minutes. Kaggle's own retry is switched off inside nested evaluations, so this is what stops one busy moment from failing a case.
6. **Grade.** `score()` reads the model's JSON (or SQL), compares it with the correct answer, and records how it went wrong.
7. **Total.** The task returns accuracy over all 120 cases, and prints the standard and hard scores separately. A call that never completed counts as wrong.

## Where InsightTrack comes in

| Piece | Comes from | Why it matters |
|---|---|---|
| Diagnosis rules | `correlationService.js`, ported to Python | The answer key is the product's real logic, checked against the JavaScript by a test |
| 23 tools | Pulse's tool registry | The model chooses among the real tools, with the real descriptions |
| Tables | InsightTrack's DuckDB schema | The SQL group writes queries for the real table layout |
| Tool outputs | InsightTrack's query functions | Same field names the real Pulse reads |

## Files

| File | Job |
|---|---|
| `insighttrack_bench/rules.py` | Answer key for diagnosis |
| `insighttrack_bench/scoring.py` | Every prompt and every grader, plus the safe SQL runner |
| `insighttrack_bench/gen_*.py` | One case generator per group |
| `insighttrack_bench/build.py` | Writes `dataset/` |
| `tasks/*.py` | What Kaggle runs, one per group |
| `scripts/parity.mjs` | Runs InsightTrack's JavaScript for the parity test |
| `scripts/export_tools.mjs` | Refreshes `data/insighttrack_tools.json` from InsightTrack |

## Why these design choices

- **One task per group, not one big task.** Kaggle's leaderboard takes one main task per notebook, and separate scores tell a better story ("great at SQL, invents causes").
- **Plain prompts that ask for JSON, not native tool calling.** Kaggle only supports automatic tool calling for Gemini, so native calls would favour one provider.
- **The SQL answer is graded by running it.** Two different queries can both be right, so checking the text would be unfair.
- **Every rule and threshold is in the diagnosis prompt.** The test is careful application, not guessing a hidden convention.
- **Synthetic data only.** No real site's visitors are used.
