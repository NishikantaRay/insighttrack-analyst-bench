# Troubleshooting

| You see | Why | Fix |
|---|---|---|
| `command not found: kaggle` | This terminal isn't using the project's tools | `export PATH="$PWD/.venv/bin:$PATH"` from the project folder |
| `Missing environment variables … MODEL_PROXY_URL` | No local model login | `kaggle b init -y` (it expires; rerun when needed) |
| 401 / unauthorized from `kaggle` | Token missing or expired | Re-export `KAGGLE_API_TOKEN`, or make a new token on kaggle.com → Settings → API |
| `Dataset not found. Attach it…` on Kaggle | Task pushed without `-d` | Push again with `-d <you>/insighttrack-analyst-bench` |
| Push fails with "task name" mismatch | The name in `push` must equal the `@task(name=…)` | Use `insighttrack_<group>` exactly, as in the loop in step 7 |
| `ModuleNotFoundError: duckdb` on Kaggle | Image without DuckDB | `tasks/sql.py` installs it automatically. If the notebook has no internet, enable it in the task's notebook settings. |
| Model scores 0% everywhere | Replies aren't JSON | Look at a reply in `runs/`. The grader accepts code fences and prose around the JSON, but not a missing JSON object. |
| Tests fail right after you edit and undo a file | Python reused an old compiled copy | `find . -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +` |
| Stray `*.task.json` / `*.run.json` in the folder | The Kaggle library writes them when tasks load | Safe to delete; they're git-ignored |
| `429 … currently experiencing heavy load` | That model is overloaded (seen with Gemini 3 Flash preview on 24 September 2026) | Each call already retries for about 2 minutes. If it still fails, try again later or pick another model with `ITBENCH_MODEL=…` |
| `403` from `kaggle b init` | Account not phone/identity verified, or bad token | Verify at kaggle.com/settings, then make a new API token |
| `max_attempts must be 1 for nested task evaluations` | Kaggle's own notice | Harmless: the task files already use 1 and retry inside each call |
| SQL cases all fail on Kaggle with a parquet or file error | Dataset uploaded without `-t`, so the tables became CSV | `kaggle datasets version -p dataset -t -m "keep parquet"` |
| `403 Forbidden … CreateDatasetVersion` | The token can't create dataset versions (limited token, or the account needs phone verification) | Check the token's permissions and verify the account at kaggle.com/settings, or click **New Version** on the dataset page and upload the changed files |
| A model's run shows `ERRORED` with `multiprocessing.context.TimeoutError` | A per-case timeout in `evaluate()` aborts the whole run in kaggle_benchmarks (seen with Qwen Thinking and Grok on 25 September 2026) | The task files now use `timeout=None`. Push again, then rerun only the failed model |
| `403 … The max estimated cost of operation ($3.84) exceeds your available quota` | Kaggle prices each call up front from its **maximum** output. Uncapped, a GPT-5.5 call was estimated at $3.84, more than the budget left | Calls now cap output at 16k tokens (`MAX_OUTPUT_TOKENS` in `scoring.py`). If the budget is simply used up, wait for the refill and rerun only the incomplete models |
| `Task name and description must each be at most 255 characters` | Kaggle's limit on task descriptions | Keep `DESCRIPTION` in each task file ≤ 255 characters (a test checks this). The long text belongs on the benchmark page |
| Most cases fail with `quota` even after the cap | The budget is spent. Kaggle reserves each call's worst case *before* running it (after the cap: about $0.50 GPT-5.5, $0.08 Haiku, $0.04 Flash-Lite), and parallel calls reserve at the same time | Wait for the refill (see kaggle.com). Then run **one model at a time**, cheapest first |
| The budget drains faster than the runs explain | Every `kaggle b t push` also runs Kaggle's default model (Gemini 3.7 Flash) over all 120 cases, about $0.27 per task and $1.10 for all four | Push only when a task file changed |
| Budget runs out mid-run | Too many cases × models | `evaluate()` caches finished cases, so rerun later and only the rest runs. Test with `ITBENCH_LIMIT=5` first. |
