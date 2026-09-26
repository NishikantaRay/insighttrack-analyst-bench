"""Summarise downloaded Kaggle runs into tables for the write-up.

    kaggle b t download insighttrack-<group> -o runs/<group>
    python scripts/analyze_runs.py                 # every group under runs/
    python scripts/analyze_runs.py --examples 3    # also show wrong answers

For each model: accuracy (over ALL cases — a case with no reply counts as
wrong), standard vs hard, per-subgroup scores, the failure-mode flags, and
cost/latency from Kaggle's own metrics. Writes runs/summary.md and
runs/summary.csv.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS = ("invented_cause", "missed_significance", "fabricated", "refused", "invalid_tool")


def load_gold(group: str) -> dict:
    path = os.path.join(ROOT, "dataset", f"cases_{group}.jsonl")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return {c["id"]: c for c in map(json.loads, fh)}


def reply_text(sub: dict) -> str:
    for conv in sub.get("conversations", []):
        for req in conv.get("requests", []):
            for content in req.get("contents", []):
                if content.get("role") == "CONTENT_ROLE_ASSISTANT":
                    return "".join(p.get("text", "") for p in content.get("parts", []))
    return ""


def cost_and_latency(sub: dict) -> tuple[float, float]:
    cost = latency = 0.0
    for conv in sub.get("conversations", []):
        m = conv.get("metrics", {})
        cost += (int(m.get("inputTokensCostNanodollars", 0)) + int(m.get("outputTokensCostNanodollars", 0))) / 1e9
        latency += float(m.get("totalBackendLatencyMs", 0)) / 1000
    return cost, latency


def no_reply_reason(sub: dict) -> str:
    """Why a case got no graded reply, from the LAST exception in its traceback.

    Matching bare numbers like "429" mislabels cases (the digits also appear
    in prompts and data), so this reads the exception name and message.
    """
    import re

    text = json.dumps(sub).replace("\\n", "\n")
    found = re.findall(r"([A-Za-z_.]*(?:Error|Exception))[:\s\\\"]+([^\n\\\"]{0,200})", text)
    if not found:
        return "other"
    name, message = found[-1][0].split(".")[-1].lstrip("n"), found[-1][1]
    if "quota" in message:
        return "quota"
    if name == "RateLimitError":
        return "overloaded"
    if name in ("InternalServerError", "APIConnectionError", "APITimeoutError"):
        return "unreachable"
    return f"{name}: {message[:60]}"


def analyze_run(path: str) -> dict:
    run = json.load(open(path))
    model = run["subruns"][0]["modelVersion"]["slug"] if run.get("subruns") else \
        os.path.basename(os.path.dirname(os.path.dirname(path)))
    total = len(run.get("subruns", []))
    if not total:
        # The whole run was aborted (e.g. the old per-case TimeoutError): no cases at all.
        return {"model": model, "cases": 0, "kaggle_score": None, "errored": 0, "cost_usd": 0.0, "latency_s": 0.0,
                "tiers": defaultdict(lambda: [0, 0]), "subgroups": defaultdict(lambda: [0, 0]),
                "flags": defaultdict(int), "wrong": [], "reasons": {"run aborted": 1}, "accuracy": 0.0,
                "complete": False}
    agg = next((r.get("numericResult", {}).get("value") for r in run.get("results", []) if "numericResult" in r), None)
    stats = {"model": model, "cases": total, "kaggle_score": agg, "errored": 0, "cost_usd": 0.0, "latency_s": 0.0,
             "tiers": defaultdict(lambda: [0, 0]), "subgroups": defaultdict(lambda: [0, 0]),
             "flags": defaultdict(int), "wrong": [], "reasons": defaultdict(int)}
    for sub in run.get("subruns", []):
        c, l = cost_and_latency(sub)
        stats["cost_usd"] += c
        stats["latency_s"] += l
        result = next((r.get("dictResult") for r in sub.get("results", []) if "dictResult" in r), None)
        if not result:
            stats["errored"] += 1
            stats["reasons"][no_reply_reason(sub)] += 1
            continue
        ok = bool(result.get("correct"))
        for key, bucket in (("difficulty", "tiers"), ("subgroup", "subgroups")):
            cell = stats[bucket][result.get(key, "?")]
            cell[0] += ok
            cell[1] += 1
        # Failure modes are counted on wrong answers only. (Runs made before the
        # grader fix marked a CORRECT "not_available" as refused.)
        if not ok:
            for f in FLAGS:
                stats["flags"][f] += bool(result.get(f))
        if not ok:
            stats["wrong"].append((result.get("id"), reply_text(sub)))
    correct = sum(v[0] for v in stats["tiers"].values())
    stats["accuracy"] = correct / total if total else 0.0
    # Only a run where every case got a reply is comparable; the rest need a rerun.
    stats["complete"] = stats["errored"] == 0
    return stats


def pct(a, n):
    return f"{a}/{n} ({a / n:.0%})" if n else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(ROOT, "runs"))
    ap.add_argument("--examples", type=int, default=0, help="wrong answers to show per model")
    args = ap.parse_args()

    rows, lines = [], ["# Results\n"]
    for task_dir in sorted(glob.glob(os.path.join(args.runs, "*", "insighttrack-*"))):
        group = os.path.basename(task_dir).removeprefix("insighttrack-").replace("-", "_")
        gold = load_gold(group)
        # Only each model's MAIN run file; an aborted run also leaves per-case files behind.
        runs = sorted(p for p in glob.glob(os.path.join(task_dir, "*", "*", "*", "*.run.json"))
                      if os.path.basename(p).startswith(f"insighttrack_{group}-run"))
        if not runs:
            continue
        # A model can have runs on several task versions (each push makes one).
        # Keep its best run: complete beats incomplete, then the newest version.
        best: dict = {}
        for p in runs:
            s = analyze_run(p)
            s["version"] = int(os.path.relpath(p, task_dir).split(os.sep)[0])
            key = (s["complete"], s["version"])
            if s["model"] not in best or key > best[s["model"]][0]:
                best[s["model"]] = (key, s)
        results = sorted((v[1] for v in best.values()), key=lambda s: (-s["complete"], -s["accuracy"]))
        lines += [f"## {group}\n", "| Model | v | Accuracy | Standard | Hard | No reply (why) | Cost | Latency (sum) |",
                  "|---|---|---|---|---|---|---|---|"]
        for s in results:
            t = s["tiers"]
            why = ", ".join(f"{k} {v}" for k, v in s["reasons"].items())
            acc = f"{s['accuracy']:.1%}" if s["complete"] else f"~~{s['accuracy']:.1%}~~ RERUN"
            lines.append(f"| {s['model']} | {s['version']} | {acc} | {pct(*t['standard'])} | {pct(*t['hard'])} | "
                         f"{s['errored']}{f' ({why})' if why else ''} | ${s['cost_usd']:.3f} | {s['latency_s']:.0f}s |")
            rows.append({"group": group, "model": s["model"], "version": s["version"], "complete": s["complete"],
                         "accuracy": round(s["accuracy"], 4),
                         "standard": t["standard"][0], "standard_n": t["standard"][1],
                         "hard": t["hard"][0], "hard_n": t["hard"][1], "no_reply": s["errored"],
                         "cost_usd": round(s["cost_usd"], 4), **{f: s["flags"][f] for f in FLAGS}})
        subgroups = sorted({g for s in results for g in s["subgroups"]})
        lines += ["", "| Subgroup | " + " | ".join(s["model"] for s in results) + " |",
                  "|---|" + "---|" * len(results)]
        for g in subgroups:
            lines.append(f"| {g} | " + " | ".join(pct(*s["subgroups"][g]) if g in s["subgroups"] else "-" for s in results) + " |")
        flags = [f for f in FLAGS if any(s["flags"][f] for s in results)]
        if flags:
            lines += ["", "| Failure flag | " + " | ".join(s["model"] for s in results) + " |",
                      "|---|" + "---|" * len(results)]
            for f in flags:
                lines.append(f"| {f} | " + " | ".join(str(s["flags"][f]) for s in results) + " |")
        if args.examples:
            for s in results:
                for cid, reply in s["wrong"][:args.examples]:
                    g = gold.get(cid, {})
                    expected = g.get("gold") or g.get("answer") or g.get("expected_tools") or g.get("expected")
                    lines += ["", f"**{s['model']} — {cid} ({g.get('subgroup', '?')})**",
                              f"- expected: `{json.dumps(expected)[:200]}`", f"- replied: `{reply.strip()[:200]}`"]
        lines.append("")

    out_md = os.path.join(args.runs, "summary.md")
    with open(out_md, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    if rows:
        with open(os.path.join(args.runs, "summary.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print("\n".join(lines))
    print(f"\nWrote {out_md}")


if __name__ == "__main__":
    main()
