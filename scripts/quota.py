"""Show today's Kaggle Benchmarks model budget.

    python scripts/quota.py            # print the budget
    python scripts/quota.py --need 2.5 # exit 1 if less than $2.50 is left (for scripts)

The Kaggle CLI (2.2.4) has no quota command, but its SDK exposes the endpoint
(/api/v1/benchmarks/tasks/quota). Uses the same login as `kaggle`
(KAGGLE_API_TOKEN or ~/.kaggle). Amounts are USD for the current day.
"""
import argparse
import sys

from kaggle import api
from kagglesdk.benchmarks.types.benchmark_tasks_api_service import ApiGetBenchmarkTaskQuotaRequest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--need", type=float, default=None, help="exit 1 if less than this many USD are left")
    args = ap.parse_args()
    api.authenticate()
    with api.build_kaggle_client() as kaggle:
        q = kaggle.benchmarks.benchmark_tasks_api_client.get_benchmark_task_quota(ApiGetBenchmarkTaskQuotaRequest())
    used, total = q.daily_quota_used, q.total_daily_quota_allowed
    left = max(total - used, 0.0)
    print(f"Daily model budget: ${used:.2f} used of ${total:.2f}  ->  ${left:.2f} left")
    # Worst-case reservation per call with the 16k output cap (measured 25 Sept 2026).
    for model, per_call in (("gemini-3.5-flash-lite", 0.041), ("claude-haiku-4-5", 0.082), ("gpt-5.5", 0.50)):
        print(f"  {model:22} reserves ~${per_call:.3f} per call  ->  room for ~{int(left / per_call)} calls at once")
    if args.need is not None and left < args.need:
        print(f"Not enough budget: need ${args.need:.2f}, have ${left:.2f}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
