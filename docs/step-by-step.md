# Step by step

Every step says **what to run**, **what you should see**, and **what to do if
it doesn't**. Run everything from the project folder.

## 0. Open a terminal in the project (every time)

```bash
cd ~/Desktop/Personal/kaggle-bench
export PATH="$PWD/.venv/bin:$PATH"
export KAGGLE_API_TOKEN=paste_your_token_here
```

- **See:** nothing. That's normal.
- **Why:** the first line opens the folder, the second makes `python` and `kaggle` use this project's copies, and the third logs you in to Kaggle.
- **Remember:** exports only last for this terminal window. Run them again in a new window.

## 1. Check the login works

```bash
kaggle b t list
```

- **See:** a table. An empty one is fine.
- **If not:** a 401 or "unauthorized" error means the token is wrong or expired. Create a new one on kaggle.com → Settings → API.

## 2. Get model access for local testing

```bash
kaggle b init -y
```

- **See:** it writes `.env`, `example_task.py` and `kaggle_benchmarks_reference.md`.
- **Why:** `.env` holds a short-lived model login, and the library reads it automatically.
- **Remember:** that login expires. If later runs complain about `MODEL_PROXY_API_KEY`, run this step again.

## 3. Ask one model one question

```bash
ITBENCH_MODEL=anthropic/claude-sonnet-5@default python smoke_test.py
```

- **See:** `✅ Pass … Bounce rate should be 29%`.
- **Pick any model** from the "LLMs Available" list that step 2 printed. Leave out `ITBENCH_MODEL` to use the default (Gemini 3 Flash).
- **If you get 429 "heavy load":** that model is busy right now. Try another one.

## 4. Try 5 cases of each group

```bash
export ITBENCH_MODEL=anthropic/claude-sonnet-5@default
ITBENCH_LIMIT=5 python tasks/diagnosis.py
ITBENCH_LIMIT=5 python tasks/tool_choice.py
ITBENCH_LIMIT=5 python tasks/data_reading.py
ITBENCH_LIMIT=5 python tasks/sql.py
```

- **Sampling:** `ITBENCH_LIMIT=5` takes one case of each kind, not just the first five.
- **Hard cases only:** add `ITBENCH_DIFFICULTY=hard` (or `standard`). On Kaggle, leave it unset to run everything.
- **Cost:** tested on 24 September 2026, Claude Sonnet 5 scored 5/5 in all four groups. The 20 calls cost $0.08.

- **See:** a per-subgroup breakdown, then an accuracy score such as `(0.6, 0.22)`, meaning 60% right ± 22%.
- **Why only 5:** model calls cost from your budget. This checks the wiring cheaply.
- **Note:** with 5 cases the score means nothing yet; the full run uses 80.

## 5. Build the dataset with your username

```bash
python -m insighttrack_bench.build --owner <your-kaggle-username>
python -m pytest
```

- **See:** the case counts (120 per group: 80 standard + 40 hard), then `91 passed`.
- **Why:** this stamps your username into `dataset/dataset-metadata.json`.

## 6. Upload the dataset to Kaggle

```bash
kaggle datasets create -p dataset -t
```

- **Always pass `-t`.** Without it, Kaggle converts table files to CSV, and the SQL group's `.parquet` tables stop working.

- **See:** a URL like `kaggle.com/datasets/<you>/insighttrack-analyst-bench`.
- **After later changes:** run `kaggle datasets version -p dataset -t -m "what changed"` instead.
- **Keep it private** until you publish the tasks, or make it public now if you prefer.

## 7. Push the four tasks

```bash
for g in tool_choice data_reading diagnosis sql; do
  kaggle b t push insighttrack_$g -f tasks/$g.py -d <you>/insighttrack-analyst-bench --wait
done
```

- **See:** each task reach a completed creation state.
- **If not:** `kaggle b t status insighttrack_<group>` shows the error.
- **Always pass `-d`:** pushing without it detaches the dataset.

> **Check your budget first:** `python scripts/quota.py` shows today's spend and what's left.
> The budget is **$10 per day** (as of 25 Sept 2026). A full 480-case run costs about $2.10 on
> Claude Sonnet 5, about $1.10 on Gemini 3.7 Flash, and under $0.10 on GPT-5.4 nano.
> The CLI has no command for this, so the script calls Kaggle's SDK directly.
>
> **Budget tips (learned the hard way):**
> - Every push re-runs Kaggle's default model on the whole task, about $1.10 for all four tasks, so push only when a task file changed.
> - Run expensive models one at a time.
> - If most cases fail with `quota`, stop and wait for the refill instead of retrying.

## 8. Pick the models and run everything

```bash
kaggle b t models            # see what's available
kaggle b t run insighttrack_diagnosis -m <model-a> -m <model-b> -m <model-c> --wait
```

- **Then:** repeat for the other three tasks.
- **See:** each run finish. Check with `kaggle b t status insighttrack_diagnosis`.
- **Aim for** at least 4–6 models, mixing fast and "thinking" models from Google, Anthropic and DeepSeek, so the post can compare them.

## 9. Download the results

```bash
kaggle b t download insighttrack_diagnosis -o runs/
```

- **Then:** repeat for each task. `runs/` holds every model's answers and scores, and the post's tables come from here.

## 10. Publish and group into one benchmark

```bash
kaggle b t publish insighttrack_tool_choice
kaggle b t publish insighttrack_data_reading
kaggle b t publish insighttrack_diagnosis
kaggle b t publish insighttrack_sql
```

- **Then:** on kaggle.com, create a benchmark named **InsightTrack Analyst Bench** and add the four tasks. Its link is what goes in the DEV post.

## 11. Write the post

Follow [writing-the-post.md](writing-the-post.md), starting from the official template link there (it sets the tags),
and submit before **11 October 2026, 11:59 PM PDT**.
