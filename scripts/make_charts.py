"""Charts for the write-up, built from runs/summary.csv (python scripts/analyze_runs.py first).

    python scripts/make_charts.py

Only models with a complete run in all four groups are plotted. Colours come from
the dataviz reference palette (slot 1 blue, slot 2 orange; validated for CVD and
contrast on the light surface). Static PNGs for the DEV post, so every value that
matters is printed as a direct label.
"""
import csv
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "charts")
GROUPS = ["tool_choice", "data_reading", "diagnosis", "sql"]

SURFACE, TEXT, TEXT2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
BLUE, ORANGE = "#2a78d6", "#eb6834"

NAMES = {
    "claude-sonnet-5@default": "Claude Sonnet 5",
    "grok-4.20-0309-reasoning": "Grok 4.20 (reasoning)",
    "gemini-3.7-flash": "Gemini 3.7 Flash",
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
    "claude-haiku-4-5@20251001": "Claude Haiku 4.5",
    "grok-4.20-0309-non-reasoning": "Grok 4.20 (no reasoning)",
    "gpt-5.4-nano-2026-03-17": "GPT-5.4 nano",
    "gpt-5.5-2026-04-23": "GPT-5.5",
}


def load():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "runs", "summary.csv"))))
    by = defaultdict(dict)
    for r in rows:
        by[r["model"].split("/")[-1]][r["group"]] = r
    models = {}
    for m, d in by.items():
        if all(g in d and d[g]["complete"] == "True" for g in GROUPS):
            models[NAMES.get(m, m)] = {
                "acc": {g: float(d[g]["accuracy"]) * 100 for g in GROUPS},
                "cost": sum(float(d[g]["cost_usd"]) for g in GROUPS),
                "invented": int(d["diagnosis"]["invented_cause"]),
                "missed": int(d["diagnosis"]["missed_significance"]),
            }
    return models


def style(ax, title, subtitle):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT2, labelsize=11, length=0)
    ax.figure.text(0.02, 0.965, title, fontsize=17, fontweight="bold", color=TEXT, va="top")
    ax.figure.text(0.02, 0.905, subtitle, fontsize=11.5, color=TEXT2, va="top")


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


def chart_diagnosis(models):
    items = sorted(models.items(), key=lambda kv: kv[1]["acc"]["diagnosis"])
    names = [k for k, _ in items]
    vals = [v["acc"]["diagnosis"] for _, v in items]
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=SURFACE)
    fig.subplots_adjust(left=0.30, right=0.93, top=0.80, bottom=0.12)
    ax.barh(names, vals, color=BLUE, height=0.62)
    for y, v in enumerate(vals):
        ax.text(v + 1.5, y, f"{v:.0f}%", va="center", fontsize=11, color=TEXT)
    ax.set_xlim(0, 110)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelcolor=TEXT, labelsize=11.5)
    style(ax, "Diagnosis: why did this page's traffic change?",
          "Share of 120 cases fully right (real or noise, direction, exact causes)")
    save(fig, "diagnosis_accuracy.png")


def chart_failures(models):
    items = sorted(models.items(), key=lambda kv: kv[1]["invented"] + kv[1]["missed"])
    names = [k for k, _ in items]
    inv = [v["invented"] for _, v in items]
    mis = [v["missed"] for _, v in items]
    fig, ax = plt.subplots(figsize=(8, 4.8), facecolor=SURFACE)
    fig.subplots_adjust(left=0.30, right=0.95, top=0.74, bottom=0.12)
    gap = 0.6  # a thin surface-coloured gap between the two segments
    ax.barh(names, inv, color=BLUE, height=0.62, edgecolor=SURFACE, linewidth=gap)
    ax.barh(names, mis, left=inv, color=ORANGE, height=0.62, edgecolor=SURFACE, linewidth=gap)
    for y, (a, b) in enumerate(zip(inv, mis)):
        if a + b == 0:
            ax.text(1, y, "none", va="center", fontsize=10.5, color=MUTED)
            continue
        if a >= 6:
            ax.text(a / 2, y, str(a), va="center", ha="center", fontsize=10.5, color="white", fontweight="bold")
        if b >= 6:
            ax.text(a + b / 2, y, str(b), va="center", ha="center", fontsize=10.5, color="white", fontweight="bold")
        ax.text(a + b + 1.2, y, f"{a + b}", va="center", fontsize=10.5, color=TEXT2)
    ax.set_xlim(0, max(i + m for i, m in zip(inv, mis)) * 1.12)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelcolor=TEXT, labelsize=11.5)
    ax.set_xlabel("Diagnosis cases (of 120)", color=TEXT2, fontsize=10.5)
    style(ax, "Two ways to be wrong about a traffic change",
          "Counted on wrong answers only")
    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
    fig.legend(handles, ["Invented a search cause that wasn't there",
                         "Called a real change noise (or noise real)"],
               loc="upper left", bbox_to_anchor=(0.015, 0.87), ncol=2, frameon=False,
               fontsize=10.5, labelcolor=TEXT2, handlelength=1.1)
    save(fig, "diagnosis_failure_modes.png")


def chart_value(models):
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    fig.subplots_adjust(left=0.10, right=0.96, top=0.82, bottom=0.13)
    offsets = {  # label placement, tuned by eye so nothing collides
        "Claude Sonnet 5": (-8, 8, "right"), "Grok 4.20 (reasoning)": (8, 6, "left"),
        "Gemini 3.7 Flash": (8, -14, "left"), "Gemini 3.5 Flash-Lite": (8, 4, "left"),
        "Claude Haiku 4.5": (8, 2, "left"), "Grok 4.20 (no reasoning)": (8, -12, "left"),
        "GPT-5.4 nano": (8, 0, "left"), "GPT-5.5": (8, 0, "left"),
    }
    for name, v in models.items():
        overall = sum(v["acc"].values()) / 4
        ax.scatter(v["cost"], overall, s=90, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
        dx, dy, ha = offsets.get(name, (8, 0, "left"))
        ax.annotate(f"{name}  {overall:.1f}%", (v["cost"], overall), xytext=(dx, dy),
                    textcoords="offset points", fontsize=10.5, color=TEXT, ha=ha, va="center")
    ax.set_xscale("log")
    ax.set_xticks([0.05, 0.1, 0.25, 0.5, 1, 2, 5])
    ax.set_xticklabels(["$0.05", "$0.10", "$0.25", "$0.50", "$1", "$2", "$5"])
    ax.minorticks_off()
    ax.set_xlim(0.04, 9)  # room for right-hand labels
    ax.set_ylim(60, 104)
    ax.set_yticks([60, 70, 80, 90, 100])
    ax.set_yticklabels(["60%", "70%", "80%", "90%", "100%"])
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Cost to run all 480 cases (log scale)", color=TEXT2, fontsize=10.5)
    style(ax, "What you get for what you pay",
          "Average accuracy across the four tasks vs. Kaggle's metered cost for the full run")
    save(fig, "score_vs_cost.png")


def main():
    models = load()
    print("models with complete runs:", ", ".join(models))
    chart_diagnosis(models)
    chart_failures(models)
    chart_value(models)


if __name__ == "__main__":
    main()
