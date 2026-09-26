"""InsightTrack Analyst Bench — SQL.

Write DuckDB SQL over InsightTrack's events and sessions tables. The query runs
read-only against sample data and is graded on its result, not its text.
80 cases.

Kaggle:  kaggle b t push insighttrack_sql -f tasks/sql.py -d <you>/insighttrack-analyst-bench --wait
         kaggle b t run insighttrack_sql -m <model> --wait
Local:   ITBENCH_LIMIT=5 [ITBENCH_MODEL=anthropic/claude-sonnet-5@default] python tasks/sql.py   (uses ./dataset and the models in .env)
"""
import glob
import json
import os
import sys

import pandas as pd

import kaggle_benchmarks as kbench

GROUP = "sql"

# Kaggle limit: 255 characters. The long version is in docs/kaggle-listing.md.
DESCRIPTION = "InsightTrack Analyst Bench: SQL. Write DuckDB SQL over InsightTrack's events and sessions tables; graded by running it, not by its text. 120 cases (80 standard + 40 hard); score = accuracy over all cases."


def find_data_dir() -> str:
    """The dataset folder: an env override, the Kaggle mount, or ./dataset locally."""
    candidates = [os.environ.get("ITBENCH_DATA"), "/kaggle/input/insighttrack-analyst-bench", "dataset", "../dataset"]
    for c in candidates:
        if c and os.path.exists(os.path.join(c, "itbench_scoring.py")):
            return c
    hits = glob.glob("/kaggle/input/**/itbench_scoring.py", recursive=True)
    if hits:
        return os.path.dirname(hits[0])
    raise FileNotFoundError(
        "Dataset not found. Attach it: kaggle b t push ... -d <you>/insighttrack-analyst-bench"
    )


DATA_DIR = find_data_dir()
sys.path.insert(0, DATA_DIR)
import itbench_scoring as its  # noqa: E402 — shipped inside the dataset

REQUIRED_SCORING = 2
if getattr(its, "SCORING_VERSION", 1) < REQUIRED_SCORING:
    # Fail once, before any model call, instead of 120 times per model.
    raise RuntimeError(
        f"The attached dataset's itbench_scoring.py is version {getattr(its, 'SCORING_VERSION', 1)}, "
        f"but this task needs {REQUIRED_SCORING}. Upload a new dataset version (dataset/itbench_scoring.py)."
    )

try:
    import duckdb  # noqa: F401
except ImportError:  # not every notebook image ships it
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "duckdb"])

# Local knobs (unset on Kaggle = all cases): ITBENCH_LIMIT=5, ITBENCH_DIFFICULTY=hard|standard
CASES = its.load_cases(DATA_DIR, GROUP, limit=int(os.environ.get("ITBENCH_LIMIT", "0")),
                       difficulty=os.environ.get("ITBENCH_DIFFICULTY") or None)
DF = pd.DataFrame({"case_json": [json.dumps(c) for c in CASES]})


@kbench.task(name="insighttrack_sql_case", store_task=False,
             description="One case of the sql group: prompt, model reply, grade.")
def one_case(llm, case_json: str) -> dict:
    case = json.loads(case_json)
    prompt = its.build_prompt(case)
    response = its.ask(llm, prompt)  # capped output + retries on "heavy load" 429s
    return its.score(case, response)


@kbench.task(name="insighttrack_sql", description=DESCRIPTION)
def insighttrack_sql(llm, df) -> tuple[float, float]:
    with kbench.client.enable_cache():
        runs = one_case.evaluate(
            llm=[llm],
            evaluation_data=df,
            on_failure="continue",  # a call that still fails after retries counts as wrong
            max_attempts=1,  # Kaggle forces 1 when nested; retries happen in one_case
            n_jobs=4,
            # No per-case limit: in kaggle_benchmarks a joblib timeout aborts the WHOLE
            # evaluation, not one case. Slow "thinking" models plus 429 retries can pass
            # 3 minutes; the model client's own HTTP timeout still stops a hung call.
            timeout=None,
            remove_run_files=True,
        )
    results = [r.result for r in runs.completed_runs]
    failed = len(df) - len(results)
    if failed:
        print(f"{failed} of {len(df)} cases failed to get a model reply (counted as wrong):")
        for r in list(runs.errored_runs)[:3]:
            print("  ", str(r.error_message)[:200])
    print(json.dumps(its.breakdown(results), indent=1))
    # Accuracy over ALL cases: a run that never completed counts as wrong.
    return its.aggregate(results, total=len(df))


def pick_model():
    """Locally, ITBENCH_MODEL picks any model listed in .env; on Kaggle, the -m model."""
    name = os.environ.get("ITBENCH_MODEL")
    if not name:
        return kbench.llm
    from kaggle_benchmarks.kaggle.models import load_model

    return load_model(name)


if __name__ == "__main__":
    insighttrack_sql.run(pick_model(), DF)
