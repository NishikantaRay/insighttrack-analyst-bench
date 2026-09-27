#!/usr/bin/env bash
# Run models on the CURRENT task version, one model and one task at a time,
# checking the daily budget before each run and stopping before it runs out.
#
#   scripts/run_models.sh claude-sonnet-5-default grok-4.20-0309-reasoning ...
#   TASKS="diagnosis sql" scripts/run_models.sh gpt-5.5-2026-04-23   # only some tasks
#
# Why: the leaderboard shows only the newest task version, and a run that hits
# the budget mid-way publishes a broken score (e.g. 0% for GPT-5.5). Never push
# the tasks again while filling the leaderboard: a push starts a new, empty version.
set -euo pipefail
cd "$(dirname "$0")/.."

# Rough full-task cost per model (USD, measured 24-25 Sept 2026), plus a margin
# for the up-front reservation of 4 parallel calls.
cost_for() {
  case "$1" in
    claude-sonnet-5-default)        echo 0.90 ;;
    gpt-5.5-2026-04-23)             echo 3.50 ;;  # ~$0.95/task measured + $2 reserved (4 x $0.50); $2.87 still hit quota on 9 cases
    gemini-3.7-flash)               echo 0.60 ;;
    grok-4.20-0309-reasoning)       echo 0.60 ;;
    claude-haiku-4-5-20251001)      echo 0.60 ;;
    *)                              echo 0.40 ;;
  esac
}

read -r -a TASKS <<< "${TASKS:-tool-choice data-reading diagnosis sql}"
[ $# -gt 0 ] || { echo "usage: $0 <model-slug> [<model-slug> ...]"; exit 2; }

for model in "$@"; do
  for t in "${TASKS[@]}"; do
    need=$(cost_for "$model")
    if ! python scripts/quota.py --need "$need" > /tmp/itbench_quota.txt; then
      cat /tmp/itbench_quota.txt
      echo "Stopping before $model on insighttrack-$t. Rerun this script tomorrow with the remaining models."
      exit 1
    fi
    echo "=== $model  ->  insighttrack-$t   ($(tail -n +1 /tmp/itbench_quota.txt | head -1))"
    kaggle b t run "insighttrack-$t" -m "$model" --wait
  done
done
echo "All requested runs finished. Download with:"
echo '  for t in tool-choice data-reading diagnosis sql; do kaggle b t download insighttrack-$t -o runs/${t//-/_}; done'
