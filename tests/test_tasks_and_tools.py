"""The Kaggle task files and the shipped tool catalogue."""
import ast
import json
import os
import subprocess

import pytest

from conftest import INSIGHTTRACK_API, ROOT, insighttrack_available
from insighttrack_bench.scoring import GROUPS


@pytest.mark.parametrize("group", GROUPS)
def test_task_file_matches_its_group(group):
    path = os.path.join(ROOT, "tasks", f"{group}.py")
    src = open(path).read()
    tree = ast.parse(src)
    names = [
        kw.value.value
        for node in ast.walk(tree) if isinstance(node, ast.Call)
        for kw in node.keywords if kw.arg == "name" and isinstance(kw.value, ast.Constant)
    ]
    main = f"insighttrack_{group}"
    # `kaggle b t push <name>` must match the @task name exactly.
    assert main in names and f"{main}_case" in names
    assert f'GROUP = "{group}"' in src
    assert f"push {main} -f tasks/{group}.py" in src
    assert f"{main}.run(pick_model(), DF)" in src
    # Model calls go through the retry wrapper, so one 429 cannot fail a case.
    assert "its.ask(llm, prompt)" in src
    assert "max_attempts=1" in src
    # A per-case timeout aborts the whole run in kaggle_benchmarks (seen on Kaggle).
    assert "timeout=None" in src
    # The run happens only when executed as a script/notebook, never on import.
    assert 'if __name__ == "__main__":' in src


def test_shipped_scoring_is_the_tested_scoring(dataset):
    shipped = open(os.path.join(dataset, "itbench_scoring.py")).read()
    assert shipped == open(os.path.join(ROOT, "insighttrack_bench", "scoring.py")).read()


def test_tool_catalogue_has_all_23_pulse_tools():
    tools = json.load(open(os.path.join(ROOT, "data", "insighttrack_tools.json")))
    assert len(tools) == 23
    assert all(t["name"] and t["description"] and "inputSchema" in t for t in tools)


@pytest.mark.skipif(not insighttrack_available(), reason="InsightTrack backend or node not found")
def test_tool_catalogue_matches_the_live_product():
    proc = subprocess.run(
        ["node", os.path.join(ROOT, "scripts", "export_tools.mjs")],
        capture_output=True, text=True, timeout=120, cwd=INSIGHTTRACK_API,
        env={**os.environ, "INSIGHTTRACK_API": INSIGHTTRACK_API},
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    live = json.loads(proc.stdout[proc.stdout.index("["):])
    shipped = json.load(open(os.path.join(ROOT, "data", "insighttrack_tools.json")))
    assert live == shipped, "InsightTrack's tools changed — re-run scripts/export_tools.mjs and rebuild"


@pytest.mark.parametrize("group", GROUPS)
def test_task_has_a_kaggle_description(group):
    src = open(os.path.join(ROOT, "tasks", f"{group}.py")).read()
    tree = ast.parse(src)
    desc = next(n.value.value for n in tree.body
                if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "DESCRIPTION")
    # Kaggle rejects the push above 255 characters ("Task name and description must each be at most 255").
    assert "120 cases" in desc and "InsightTrack" in desc and len(desc) <= 255
    assert f'name="insighttrack_{group}", description=DESCRIPTION' in src


def test_dataset_metadata_meets_kaggle_limits(dataset):
    meta = json.load(open(os.path.join(dataset, "dataset-metadata.json")))
    assert 6 <= len(meta["title"]) <= 50
    assert 20 <= len(meta["subtitle"]) <= 80
    assert len(meta["licenses"]) == 1 and meta["description"].strip()
    shipped = set(os.listdir(dataset)) - {"dataset-metadata.json"}
    assert {r["path"] for r in meta["resources"]} == shipped  # every file described


@pytest.mark.parametrize("group", GROUPS)
def test_task_requires_the_shipped_scoring_version(group, dataset):
    """A stale dataset copy must stop the task before any model call."""
    import importlib.util

    src = open(os.path.join(ROOT, "tasks", f"{group}.py")).read()
    required = int(src.split("REQUIRED_SCORING = ")[1].split()[0])
    spec = importlib.util.spec_from_file_location("shipped", os.path.join(dataset, "itbench_scoring.py"))
    shipped = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shipped)
    assert shipped.SCORING_VERSION == required
    # Everything the task file calls on `its.` must exist in the shipped copy.
    for name in ("ask", "build_prompt", "score", "aggregate", "breakdown", "load_cases"):
        assert f"its.{name}(" in src
        assert hasattr(shipped, name), name


def test_parquet_column_descriptions_match_the_tables(dataset):
    """Kaggle matches column descriptions by position, so they must list every column in order."""
    import duckdb

    meta = json.load(open(os.path.join(dataset, "dataset-metadata.json")))
    for res in meta["resources"]:
        if res["path"].endswith(".parquet"):
            actual = [r[0] for r in duckdb.sql(f"DESCRIBE SELECT * FROM '{os.path.join(dataset, res['path'])}'").fetchall()]
            assert [f["name"] for f in res["schema"]["fields"]] == actual, res["path"]
