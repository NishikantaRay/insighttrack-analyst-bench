# Writing the DEV post

**Use the official template.** It pre-fills the title, the tags and the four required sections:
https://dev.to/new?prefill=---%0Atitle%3A%20%0Apublished%3A%20%0Atags%3A%20devchallenge%2C%20kagglechallenge%2C%20ai%2C%20machinelearning%0A---%0A%0A%2AThis%20is%20a%20submission%20for%20the%20%5BKaggle%20Benchmarking%20Challenge%5D%28https%3A%2F%2Fdev.to%2Fchallenges%2Fkaggle-2026-09-23%29%2A%0A%0A%23%23%20What%20I%20Benchmarked%0A%3C%21--%20What%20task%28s%29%20did%20you%20run%3F%20Tell%20us%20what%20capability%20or%20behavior%20you%20set%20out%20to%20measure%20and%20why%20it%20interested%20you.%20--%3E%0A%0A%23%23%20Models%20Tested%0A%3C%21--%20Which%20models%20did%20you%20run%20your%20benchmark%20against%2C%20and%20why%20did%20you%20pick%20them%3F%20--%3E%0A%0A%23%23%20Findings%0A%3C%21--%20Share%20your%20results%20and%20the%20main%20insights.%20What%20surprised%20you%3F%20What%20would%20you%20measure%20next%3F%20--%3E%0A%0A%23%23%20My%20Benchmark%0A%3C%21--%20Required%3A%20share%20a%20link%20to%20your%20benchmark%20on%20Kaggle%20so%20judges%20and%20readers%20can%20check%20it%20out.%20--%3E

- **Tags in the template:** `devchallenge, kagglechallenge, ai, machinelearning`. The announcement's text says `#kagglebenchmarkchallenge`, but DEV allows 4 tags and the official template uses these. Keep them.
- **Required sections, in this order:** What I Benchmarked, Models Tested, Findings, My Benchmark.
- **The link must be to the *benchmark*** (the page grouping the four tasks), not to a single task: "Submissions must include a link to your benchmark on Kaggle to be eligible."
- **Deadline:** 11 October 2026, 11:59 PM PDT. Winners are announced 5 November.
- **Judged on:** insights shared, writing quality, creativity in approach.

## Suggested structure

1. **The itch (2–3 sentences).** "I built an open-source analytics tool with an AI analyst. Before choosing which model runs it, I tested them on its actual job." Link [InsightTrack](https://github.com/NishikantaRay/InsightTrack).
2. **What I'm benchmarking and why.**
   - The four groups, one line each.
   - Lead with diagnosis. Its question is *do models invent a cause when nothing happened?*
3. **Models tested.** List them, and mark which are "thinking" models and which are fast.
4. **Results.**
   - **One table:** model × group accuracy.
   - **One chart:** the invented-cause rate on the not-significant and decoy cases.
5. **What surprised me.** Pick 2–3 real findings from `runs/`, with one quoted model reply each. Good places to look:
   - the gap between invented causes and accuracy
   - SQL that runs but answers the wrong question
   - made-up numbers on unanswerable questions
   - thinking models compared with fast ones
6. **The decision.** "Pulse will use model X because …". Concrete insight is exactly what the judges score.
7. **How it's built.** Why the answers can be trusted:
   - the answer key is the product's own rules, checked against its JavaScript
   - SQL is graded by running it
   - everything is synthetic and reproducible
8. **Limits.** "Correct means correct by InsightTrack's rules", the synthetic data, and a single run per model.
9. **Links.** The Kaggle benchmark (required), the dataset, and the InsightTrack repo.
10. **Credits.**
    - Kaggle Benchmarks and its `dataset_evaluation.py` example.
    - Related benchmarks: BFCL, τ-bench, InfiAgent-DABench, DSBench, Spider 2.0, BIRD. Say how this one differs.

## First signal (24 September 2026, 8 hard cases per group)

| Model | Tool choice | Data reading | Diagnosis | SQL |
|---|---|---|---|---|
| Claude Sonnet 5 | 8/8 | 8/8 | 8/8 | 8/8 |
| GPT-5.4 nano | 5/8 | 4/8 | 1/8 | 6/8 |

Real nano mistakes on diagnosis, all checked by hand:
- **Boundary:** traffic fell 200 → 170, exactly 15% and 30 views, so significant. Nano said "not significant".
- **Direction rules:** traffic dropped, and nano still listed `rank_gain` and `ai_citation_gained`, which only count when traffic rises.
- **Domains:** the AI answer quoted `www.<site>`, the site itself. Nano called it a displacement, which is an invented cause.

A sample this small is only a signal. Report the full 120-per-group runs. The likely
story is the gap between frontier and small or cheap models, and *which kinds* of
mistake each makes, since top models may be near the ceiling.

## Numbers worth pulling from `runs/`

- Accuracy per group per model, from each task's result.
- Per subgroup, the breakdown each task prints: `invented_cause`, `fabricated`, `invalid_tool`, `missed_significance` and `refused`.
- Failure rates among the unanswerable cases (39) and the decoy + not-significant cases (28), which make the sharpest comparisons.
- Standard against hard for each model. Each task prints `TIER standard` and `TIER hard`.

## Before you submit

- [ ] The Kaggle benchmark link opens while logged out, so it's public.
- [ ] Every number in the post comes from `runs/`, not memory.
- [ ] Credits are included, since the rules require crediting prior work.
- [ ] The tags are the template's own (`devchallenge, kagglechallenge, ai, machinelearning`).
- [ ] The link is to the **benchmark** page, not a task.
