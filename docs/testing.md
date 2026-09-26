# Testing

```bash
python -m pytest            # 91 tests, under a second, no model calls
```

## What the tests prove

| File | Proves |
|---|---|
| `tests/test_rules.py` | Each ported rule behaves like InsightTrack: both significance floors, jitter ignored, direction-only causes, subdomains count as the site, and JavaScript-style rounding |
| `tests/test_parity.py` | **The Python answer key equals InsightTrack's JavaScript** on all 120 diagnosis cases, plus 1,500 random ones with 1–3 keywords and lookalike or `www.` domains |
| `tests/test_generate.py` | Rebuilds are byte-identical, each group has 120 unique cases (80 standard + 40 hard), every diagnosis answer can be recomputed, every cause code appears, tool names and arguments are real, and every SQL reference query reproduces its answer |
| `tests/test_scoring.py` | A perfect model scores 100% and garbage scores 0; each failure flag fires; unsafe SQL is refused; the model's SQL can't read files or change tables |
| `tests/test_tasks_and_tools.py` | Each Kaggle file's task name matches its push command; the shipped scoring file is the tested one; the tool list matches the live InsightTrack registry |

## The hard builders check themselves

Each hard diagnosis builder writes down the answer it *intends* (for example "200 → 170
is exactly 15%, so significant; 12 → 15 is exactly 3 places, so `rank_drop`"). The build
fails if the ported rules disagree. This caught a real mistake while writing it: a case
meant to test `page_one_exit` alone went from #8 to #12, which is 4 places, so
`rank_drop` fired too. It now goes from #9 to #11.

## Needs InsightTrack for two tests

The parity and live-tool tests run InsightTrack's own code with Node. They look for it at
`~/Desktop/Personal/InsightTrack/apps/analytics-api`, or wherever `INSIGHTTRACK_API` points.
Without it they **skip**, and the rest still run.

## Is the parity test real?

Yes. It was checked by changing the rank threshold in `rules.py` from 3 to 2:
`test_random_inputs_match_the_product` failed straight away, and passed again once
the threshold was restored.

## When InsightTrack changes

If a tool or rule changes in InsightTrack, a test fails and says so. To catch up:

```bash
INSIGHTTRACK_API=~/Desktop/Personal/InsightTrack/apps/analytics-api \
  node scripts/export_tools.mjs > data/insighttrack_tools.json   # tools
# rules: port the change into insighttrack_bench/rules.py
python -m insighttrack_bench.build --owner <you> && python -m pytest
kaggle datasets version -p dataset -t -m "sync with InsightTrack"
```
