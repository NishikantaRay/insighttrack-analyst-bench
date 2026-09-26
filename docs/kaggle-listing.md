# Kaggle listing: names, descriptions, updates

Everything that appears on Kaggle, and where it comes from.

| Kaggle page | Name / URL | Where its text lives |
|---|---|---|
| Dataset | `nishikantaray/insighttrack-analyst-bench` | `insighttrack_bench/build.py` (`TITLE`, `SUBTITLE`, `dataset_description()`, `FILE_DESCRIPTIONS`), written to `dataset/dataset-metadata.json` |
| Task: tool choice | `insighttrack-tool-choice` | `DESCRIPTION` in `tasks/tool_choice.py` |
| Task: data reading | `insighttrack-data-reading` | `DESCRIPTION` in `tasks/data_reading.py` |
| Task: diagnosis | `insighttrack-diagnosis` | `DESCRIPTION` in `tasks/diagnosis.py` |
| Task: SQL | `insighttrack-sql` | `DESCRIPTION` in `tasks/sql.py` |
| Benchmark | InsightTrack Analyst Bench | Pasted on kaggle.com (text below) |

**The leaderboard shows only each task's newest version.** Runs on older versions don't
appear. So:
1. **Don't push the tasks again** once the leaderboard is filling up. A push starts a new, empty version.
2. **Run models with `scripts/run_models.sh <model> …`.** It runs one model and one task at a time, and stops before the daily budget runs out, so no half-broken score gets published.
3. **Check the result with `python scripts/leaderboard.py`**, which needs no login.

**Never rename a task.** The name *is* the URL, and a new name makes a new, empty task
that loses every run. Change descriptions freely.

## Updating the dataset's description (no new version)

```bash
python -m insighttrack_bench.build --owner nishikantaray
kaggle datasets metadata --update -p dataset nishikantaray/insighttrack-analyst-bench
```

- **What it changes:** the title, subtitle, description, tags and per-file notes, without uploading files.
- **If it returns 403:** the token can't edit datasets. Edit the same text on the dataset page instead: open `dataset/dataset-metadata.json` and copy the fields across.

## Updating the task descriptions

Pushing again creates a **new task version** (v2). Runs belong to a version, so after
pushing, run the models on the new version:

```bash
for g in tool_choice data_reading diagnosis sql; do
  kaggle b t push insighttrack_$g -f tasks/$g.py -d nishikantaray/insighttrack-analyst-bench --wait
done
```

## Benchmark page (paste on kaggle.com)

The benchmark page can only be created on the website. Kaggle's SDK (as of CLI 2.2.4) can
create and publish *tasks*, schedule runs and read leaderboards, but has no call to
create a benchmark.

- **Where:** Benchmarks → create a benchmark, then add the four tasks.
- **Name:** `InsightTrack Analyst Bench`
- **Short description:**

> Which LLM should power the AI analyst in a real analytics product? 480 auto-graded cases from InsightTrack's actual job: tool choice, data reading, traffic-change diagnosis and SQL.

- **Full description:**

> **InsightTrack Analyst Bench** gives models the job of *Pulse*, the AI analyst inside
> [InsightTrack](https://github.com/NishikantaRay/InsightTrack), an open-source web analytics
> platform, and grades every answer automatically.
>
> | Task | What it tests |
> |---|---|
> | Tool choice | Picking the right one of 23 real tools, with the right arguments, or "none" |
> | Data reading | Reading a real-shaped tool result correctly, and saying "not_available" instead of inventing a number |
> | Diagnosis | Deciding whether a traffic change is real and what caused it, graded by the product's own rules |
> | SQL | Writing DuckDB queries over the product's tables, graded by running them |
>
> Each task has 120 cases: 80 standard + 40 hard. Beyond accuracy, the graders record *how*
> models fail: invented causes, made-up numbers, tools that don't exist, noise mistaken for change.
> All data is synthetic and reproducible. Built for the DEV x Kaggle Benchmarking Challenge.

- **Tags (if asked):** benchmark, llm, sql, data analytics
