# Social posts: InsightTrack Analyst Bench

Replace `[DEV link]` with the published DEV post URL before posting.
Leaderboard: https://www.kaggle.com/benchmarks/nishikantaray/insighttrack-analyst-bench

---

## LinkedIn

My analytics product has an AI analyst. Before trusting a model with it, I tested 8 of them on its real job.

The setup: 480 questions from InsightTrack's actual work. Pick the right tool, read the data, explain why traffic changed, write the SQL. Every answer is checked by my product's own code, not by another AI.

What I found:
→ Picking the right tool is solved. Every model scored 93–100%.
→ Explaining *why* traffic moved is where they split. The top models scored 100%; cheaper ones scored 20–49%.
→ Same model, reasoning on vs. off: 100% vs. 35%.
→ Cheap models fail in two opposite ways. One invented causes 34 times. Another called a 47% traffic drop "not significant".

The most useful lesson for anyone building AI features: the worst answer isn't "I don't know". It's a confident wrong one.

Built for the DEV × Kaggle Benchmarking Challenge.
Full write-up: [DEV link]
Leaderboard: https://www.kaggle.com/benchmarks/nishikantaray/insighttrack-analyst-bench

#AI #LLM #Kaggle #devchallenge #BuildInPublic

---

## LinkedIn: explainer post (image: `post/social/explainer-light.png`; dark version: `explainer.png`)

InsightTrack × Kaggle × DEV: my hackathon project in one picture. 👇

I build InsightTrack, an open-source web analytics app. Its AI analyst, Pulse, answers questions like "why did traffic to /pricing drop?"

Pulse needs a model behind it, so I made the choice a hackathon project.

① I turned Pulse's real job into 480 test questions.
② Every answer is checked by InsightTrack's own code. No AI grades AI.
③ Kaggle ran 8 models on the same questions.
④ I wrote up what happened on DEV.

The results:
✅ Claude Sonnet 5, GPT-5.5, Grok 4.20 (reasoning) and Gemini 3.7 Flash all scored 97–100%.
⚠️ The cheaper models dropped to 67–81%. On "why did traffic change?" they scored just 20–49%.
🔁 Same model, reasoning on vs. off: 100% vs. 35%.

The hardest skill wasn't calling tools. It was knowing when nothing happened, and saying so.

📊 Leaderboard: https://www.kaggle.com/benchmarks/nishikantaray/insighttrack-analyst-bench
📝 Full write-up: [DEV link]

#Kaggle #devchallenge #kagglechallenge #AI #LLM #BuildInPublic

---

## X / Twitter (thread)

**1/**
I gave 8 LLMs my analytics product's AI job, with 480 auto-graded questions.

The cheap ones fail in one of two ways: they invent a reason, or they shrug. 🧵

**2/**
The job is being Pulse, the AI analyst in InsightTrack. Pick a tool, read the data, explain why traffic changed, write the SQL.

The answers come from the product's own code. No AI grades AI.

**3/**
Tool calling is solved: 93–100% for everyone.

"Why did traffic drop?" is not. Top models scored 100%, and cheaper ones 20–49%.

**4/**
Same model, reasoning on vs. off:
Grok 4.20 → 100% vs. 35% on diagnosis.

If your assistant answers *why* questions, reasoning isn't optional.

**5/**
The two failure types:
🔔 The alarmist blamed Google rank 34 times when search wasn't the cause.
🤷 The shrugger saw a 47% traffic drop and said "not significant".

The shrugger is the dangerous one.

**6/**
My favourite bug was my own. Two rules in my prompt clashed, and GPT-5.5 followed the literal one. All 4 of its misses came from that.

A benchmark's prompt is code too.

**7/**
Final: Sonnet 5 100 · GPT-5.5 99.2 · Grok (reasoning) 97.9 · Gemini 3.7 Flash 97.7 (at half the cost).

Write-up: [DEV link]
#kagglechallenge #devchallenge

---

## X / Twitter (single post)

Tested 8 LLMs on my analytics product's real AI job: 480 questions, graded by the product's own code.

Tool calling: solved (93–100%).
"Why did traffic drop?": 100% for top models, 20–49% for cheap ones.
Same model, reasoning on vs. off: 100% vs. 35%.

[DEV link] #kagglechallenge

---

## Instagram / Threads (caption, with assets/cover.png or a chart)

I asked 8 AI models to do my analytics app's job. 📊

Easy part: picking the right tool. Everyone passed.
Hard part: explaining *why* traffic changed.

• Top models: 100%
• Cheaper models: 20–49%
• One model saw a 47% drop and said "nothing happened" 🤷

Lesson: a confident wrong answer is worse than "I don't know".

Built for the DEV × Kaggle Benchmarking Challenge. Link in bio.
#AI #MachineLearning #Kaggle #BuildInPublic #DevCommunity

---

## Short hook lines (for any platform)

- "Tool calling is solved. Knowing when *nothing* happened isn't."
- "The cheapest model saw traffic fall 47% and said 'not significant'."
- "Same model. Reasoning on: 100%. Reasoning off: 35%."
- "My AI benchmark's best bug was in my own prompt."

---

## Which image goes with which post

All in `post/social/`. Regenerate with `python scripts/make_social.py`.

| Post | Image |
|---|---|
| LinkedIn square post | `square-light.png` (1200×1200, light, logos) |
| LinkedIn explainer post | `explainer-light.png` (light, real logos), or `explainer.png` (dark) |
| LinkedIn (first post above) | `carousel-linkedin.pdf`: upload as a **document** so it shows as a swipeable carousel. Or `landscape.png` for a single image |
| X / Twitter thread | Tweet 1: `landscape.png` · tweet 3: `carousel-03.png` · tweet 4: `carousel-04.png` · tweet 5: `carousel-05.png` · tweet 7: `carousel-06.png` |
| X single post | `square.png` |
| Instagram feed | `carousel-01.png` … `carousel-07.png` as one carousel post |
| Instagram / LinkedIn story | `story.png` (add a link sticker to the DEV post) |
| DEV post cover | `cover-light-dev.png` (1600×672, DEV's cover shape). Also at `post/cover-dev.png` |
| Kaggle benchmark / dataset cover | `cover-light.png` (1600×800) |
