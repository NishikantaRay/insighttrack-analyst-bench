"""Print the public benchmark leaderboard (no login needed once it is public).

    python scripts/leaderboard.py

Note: Kaggle's leaderboard shows only each task's NEWEST version. Runs on older
versions (e.g. our v1 results) are not shown, so every model must be run on the
current version, and the tasks must not be pushed again (a push starts an empty version).
"""
import json
import urllib.request

URL = "https://www.kaggle.com/api/v1/benchmarks/nishikantaray/insighttrack-analyst-bench/leaderboard"


def main():
    with urllib.request.urlopen(URL) as r:
        data = json.load(r)
    if "rows" not in data:
        print("Not readable:", data, "(is the benchmark public?)")
        return
    tasks = ["tool-choice", "data-reading", "diagnosis", "sql"]
    print(f"{'model':32} {'overall':>8} " + " ".join(f"{t:>13}" for t in tasks) + "   task version")
    for row in data["rows"]:
        cells, overall, versions = {}, None, set()
        for t in row["taskResults"]:
            res = t.get("result", {})
            val = res.get("numericResult", {}).get("value") if res.get("hasNumericResult") else None
            slug = (t.get("benchmarkTaskSlug") or "").rsplit("/", 1)[-1].removeprefix("insighttrack-")
            if not slug:
                overall = val
            else:
                cells[slug] = val
                versions.add(t.get("taskVersion"))
        fmt = lambda v: "-" if v is None else f"{v * 100:.1f}"  # noqa: E731
        print(f"{row['modelVersionSlug'][:32]:32} {fmt(overall):>8} "
              + " ".join(f"{fmt(cells.get(t)):>13}" for t in tasks) + f"   v{','.join(map(str, sorted(versions)))}")


if __name__ == "__main__":
    main()
