"""Smoke test: proves the local -> Kaggle loop works before the real benchmark.

One tiny InsightTrack-flavoured question with a known answer.
Local:   python smoke_test.py
Kaggle:  kaggle b t push insighttrack_smoke_test -f smoke_test.py --wait
         kaggle b t run insighttrack_smoke_test --wait
"""
import os

import kaggle_benchmarks as kbench


@kbench.task(name="insighttrack_smoke_test")
def bounce_rate(llm, sessions: int, bounces: int, answer: str):
    response = llm.prompt(
        f"A page had {sessions} sessions and {bounces} of them bounced. "
        "What is the bounce rate as a whole-number percentage? "
        "Reply with the number only, like 42."
    )
    kbench.assertions.assert_contains_regex(
        rf"\b{answer}\b", response, expectation=f"Bounce rate should be {answer}%."
    )


if __name__ == "__main__":
    # ITBENCH_MODEL=<name from .env> picks another model when the default is busy.
    name = os.environ.get("ITBENCH_MODEL")
    if name:
        from kaggle_benchmarks.kaggle.models import load_model

        llm = load_model(name)
    else:
        llm = kbench.llm
    bounce_rate.run(llm=llm, sessions=200, bounces=58, answer="29")
