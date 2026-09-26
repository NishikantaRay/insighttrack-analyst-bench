"""Group 4 — SQL over InsightTrack's DuckDB tables.

Builds two months of synthetic `events` and `sessions` rows using the exact
column layout of InsightTrack's DuckDB schema (src/schema/schema.js), then asks
questions whose gold result is produced by running a reference query on the
same data. Models are graded on what their SQL returns, not on how it looks.

`daily_stats` is deliberately left out: InsightTrack's rollup writes bounces=0,
so questions over it would have no fair answer.
"""
from __future__ import annotations

import datetime as dt
import json
import random
import uuid

SITE_ID = "site_demo"
DOMAIN = "https://studynotes.dev"
START = dt.date(2026, 7, 1)
DAYS = 62  # July + August 2026

PAGES = ["/", "/pricing", "/signup", "/docs/getting-started", "/blog/acid-properties-explained",
         "/blog/api-rate-limiting", "/blog/sql-joins-visual-guide", "/blog/gdpr-for-developers",
         "/changelog", "/about"]
ENTRY_WEIGHTS = [20, 8, 4, 6, 18, 12, 14, 8, 3, 2]
DEVICES = [("desktop", 55), ("mobile", 38), ("tablet", 7)]
COUNTRIES = [("IN", 35), ("US", 25), ("GB", 10), ("DE", 8), ("BR", 7), ("CA", 5), ("AU", 5), ("FR", 5)]
CITIES = {"IN": "Bengaluru", "US": "Austin", "GB": "London", "DE": "Berlin", "BR": "São Paulo",
          "CA": "Toronto", "AU": "Sydney", "FR": "Paris"}
REFERRERS = [
    ("https://www.google.com/", 35, None), ("", 25, None), ("https://twitter.com/", 8, ("twitter", "social", "launch-week")),
    ("https://www.reddit.com/", 5, None), ("https://mail.google.com/", 7, ("newsletter", "email", "weekly-digest")),
    ("https://www.bing.com/", 5, None), ("https://news.ycombinator.com/", 5, None),
    ("https://www.linkedin.com/", 5, ("linkedin", "social", "launch-week")), ("https://someblog.io/post", 5, None),
]
BROWSERS = {"desktop": ["Chrome", "Firefox", "Safari", "Edge"], "mobile": ["Chrome", "Safari"], "tablet": ["Safari", "Chrome"]}
OSES = {"desktop": ["Windows", "macOS", "Linux"], "mobile": ["Android", "iOS"], "tablet": ["iOS", "Android"]}


def _pick(rng, weighted):
    return rng.choices([w[0] for w in weighted], weights=[w[1] for w in weighted])[0]


def build_tables(seed: int = 17) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    uid = lambda: str(uuid.UUID(int=rng.getrandbits(128)))  # noqa: E731 — deterministic ids
    users = [uid() for _ in range(1600)]
    seen_users: set[str] = set()
    events, sessions = [], []

    for day in range(DAYS):
        date = START + dt.timedelta(days=day)
        weekend = date.weekday() >= 5
        n = max(5, round(rng.gauss(30 if weekend else 45, 6)))
        for _ in range(n):
            user = rng.choice(users)
            returning = user in seen_users
            seen_users.add(user)
            device = _pick(rng, DEVICES)
            country = _pick(rng, COUNTRIES)
            ref_row = rng.choices(REFERRERS, weights=[r[1] for r in REFERRERS])[0]
            referrer, utm = ref_row[0], (ref_row[2] if rng.random() < 0.8 else None)
            browser, os_ = rng.choice(BROWSERS[device]), rng.choice(OSES[device])

            pv = 1 if rng.random() < 0.45 else min(8, 2 + int(rng.expovariate(0.6)))
            t = dt.datetime.combine(date, dt.time()) + dt.timedelta(seconds=rng.randint(0, 86_000 - 8 * 300))
            path = rng.choices(PAGES, weights=ENTRY_WEIGHTS)[0]
            sid = uid()
            session_events = []
            for i in range(pv):
                if i:
                    t += dt.timedelta(seconds=rng.randint(10, 300))
                    path = rng.choice(PAGES)
                session_events.append(("pageview", path, t, None))
                custom = None
                if path == "/signup" and rng.random() < 0.3:
                    custom = "signup"
                elif path.startswith("/blog/") and rng.random() < 0.08:
                    custom = "download_pdf"
                elif rng.random() < 0.02:
                    custom = "newsletter_subscribe"
                if custom:
                    session_events.append(("custom", path, t + dt.timedelta(seconds=rng.randint(1, 5)),
                                           json.dumps({"name": custom})))

            for etype, epath, ets, props in session_events:
                events.append({
                    "id": uid(), "site_id": SITE_ID, "user_id": user, "session_id": sid, "type": etype,
                    "url": DOMAIN + epath, "path": epath, "referrer": referrer, "device": device,
                    "browser": browser, "os": os_, "country": country, "city": CITIES[country],
                    "timestamp": ets, "properties": props,
                    "utm_source": utm[0] if utm else None, "utm_medium": utm[1] if utm else None,
                    "utm_campaign": utm[2] if utm else None, "utm_term": None, "utm_content": None,
                })
            pageviews = [e for e in session_events if e[0] == "pageview"]
            started, ended = session_events[0][2], session_events[-1][2]
            sessions.append({
                "id": sid, "site_id": SITE_ID, "user_id": user, "started_at": started, "ended_at": ended,
                "duration": int((ended - started).total_seconds()), "pageviews": len(pageviews),
                "entry_page": pageviews[0][1], "exit_page": pageviews[-1][1], "referrer": referrer,
                "device": device, "browser": browser, "os": os_, "country": country,
                "is_bounce": len(pageviews) == 1, "is_returning": returning,
                "utm_source": utm[0] if utm else None, "utm_medium": utm[1] if utm else None,
                "utm_campaign": utm[2] if utm else None,
            })
    return events, sessions


def load_into_duckdb(events, sessions):
    import duckdb
    import pandas as pd

    con = duckdb.connect(":memory:")
    from .scoring import SQL_SCHEMA
    con.execute(SQL_SCHEMA)
    for table, rows in (("events", events), ("sessions", sessions)):
        df = pd.DataFrame(rows)  # noqa: F841 — referenced by name in the SQL below
        con.execute(f"INSERT INTO {table} SELECT * FROM df")
    return con


# ── questions ────────────────────────────────────────────────────────────────

def _range(rng, max_len=14):
    start = START + dt.timedelta(days=rng.randint(0, DAYS - max_len - 1))
    return start, start + dt.timedelta(days=rng.randint(3, max_len))


def _date_cond(col, d1, d2):
    return f"CAST({col} AS DATE) BETWEEN DATE '{d1}' AND DATE '{d2}'"


def t_page_views(rng):
    p, (d1, d2) = rng.choice(PAGES), _range(rng)
    return (f"How many pageviews did {p} get between {d1} and {d2}? Return one column: pageviews.",
            f"SELECT COUNT(*) FROM events WHERE type = 'pageview' AND path = '{p}' AND {_date_cond('timestamp', d1, d2)}",
            False)


def t_unique_visitors(rng):
    d = START + dt.timedelta(days=rng.randint(0, DAYS - 1))
    return (f"How many unique visitors (distinct users with any event) were there on {d}? Return one column: visitors.",
            f"SELECT COUNT(DISTINCT user_id) FROM events WHERE CAST(timestamp AS DATE) = DATE '{d}'",
            False)


def t_top_pages(rng):
    n, (d1, d2) = rng.choice([3, 5]), _range(rng)
    return (f"List the top {n} pages by pageviews between {d1} and {d2}, most viewed first; break ties by path A→Z. "
            "Return columns: path, pageviews.",
            f"SELECT path, COUNT(*) AS pageviews FROM events WHERE type = 'pageview' AND {_date_cond('timestamp', d1, d2)} "
            f"GROUP BY path ORDER BY pageviews DESC, path ASC LIMIT {n}",
            True)


def t_bounce_rate(rng):
    device, (d1, d2) = rng.choice(["desktop", "mobile", "tablet"]), _range(rng, 30)
    return (f"What percentage of {device} sessions that started between {d1} and {d2} were bounces? "
            "Round to 1 decimal place. Return one column: bounce_rate.",
            f"SELECT ROUND(100.0 * AVG(CASE WHEN is_bounce THEN 1 ELSE 0 END), 1) FROM sessions "
            f"WHERE device = '{device}' AND {_date_cond('started_at', d1, d2)}",
            False)


def t_top_countries(rng):
    d1, d2 = _range(rng, 30)
    return (f"Which 3 countries had the most sessions starting between {d1} and {d2}? Most sessions first; break ties by "
            "country code A→Z. Return columns: country, sessions.",
            f"SELECT country, COUNT(*) AS sessions FROM sessions WHERE {_date_cond('started_at', d1, d2)} "
            "GROUP BY country ORDER BY sessions DESC, country ASC LIMIT 3",
            True)


def t_entry_duration(rng):
    p, (d1, d2) = rng.choice(PAGES[:8]), _range(rng, 30)
    return (f"What was the average session duration in seconds for sessions that started between {d1} and {d2} "
            f"with entry page {p}? Round to 1 decimal place. Return one column: avg_duration.",
            f"SELECT ROUND(AVG(duration), 1) FROM sessions WHERE entry_page = '{p}' AND {_date_cond('started_at', d1, d2)}",
            False)


def t_utm_sessions(rng):
    s, (d1, d2) = rng.choice(["newsletter", "twitter", "linkedin"]), _range(rng, 30)
    return (f"How many sessions with utm_source '{s}' started between {d1} and {d2}? Return one column: sessions.",
            f"SELECT COUNT(*) FROM sessions WHERE utm_source = '{s}' AND {_date_cond('started_at', d1, d2)}",
            False)


def t_daily_page(rng):
    p = rng.choice(PAGES[:7])
    d1 = START + dt.timedelta(days=rng.randint(0, DAYS - 8))
    d2 = d1 + dt.timedelta(days=6)
    return (f"For {p}, how many pageviews were there on each day from {d1} to {d2}? Oldest day first; leave out "
            "days with no pageviews. Return columns: date, pageviews.",
            f"SELECT CAST(timestamp AS DATE) AS date, COUNT(*) AS pageviews FROM events WHERE type = 'pageview' "
            f"AND path = '{p}' AND {_date_cond('timestamp', d1, d2)} GROUP BY 1 ORDER BY 1",
            True)


def t_custom_events(rng):
    name, (d1, d2) = rng.choice(["signup", "download_pdf", "newsletter_subscribe"]), _range(rng, 30)
    return (f"How many '{name}' custom events were recorded between {d1} and {d2}? Return one column: events.",
            f"SELECT COUNT(*) FROM events WHERE type = 'custom' AND json_extract_string(properties, '$.name') = '{name}' "
            f"AND {_date_cond('timestamp', d1, d2)}",
            False)


def t_search_share(rng):
    d1, d2 = _range(rng, 30)
    return (f"What percentage of sessions that started between {d1} and {d2} came from Google Search or Bing "
            "(referrer exactly 'https://www.google.com/' or 'https://www.bing.com/')? "
            "Round to 1 decimal place. Return one column: search_share.",
            f"SELECT ROUND(100.0 * AVG(CASE WHEN referrer IN ('https://www.google.com/', 'https://www.bing.com/') "
            f"THEN 1 ELSE 0 END), 1) FROM sessions WHERE {_date_cond('started_at', d1, d2)}",
            False)


def t_returning_by_device(rng):
    d1, d2 = _range(rng, 30)
    return (f"For sessions starting between {d1} and {d2}, how many were from returning visitors on each device? "
            "Return columns: device, sessions (any order).",
            f"SELECT device, COUNT(*) FROM sessions WHERE is_returning AND {_date_cond('started_at', d1, d2)} GROUP BY device",
            False)


def t_top_exit(rng):
    d1, d2 = _range(rng, 30)
    return (f"Which page was the most common exit page for sessions that started between {d1} and {d2}? "
            "Return one column: exit_page.",
            f"SELECT exit_page FROM sessions WHERE {_date_cond('started_at', d1, d2)} "
            "GROUP BY exit_page ORDER BY COUNT(*) DESC LIMIT 1",
            True)


TEMPLATES = [t_page_views, t_unique_visitors, t_top_pages, t_bounce_rate, t_top_countries, t_entry_duration,
             t_utm_sessions, t_daily_page, t_custom_events, t_search_share, t_returning_by_device, t_top_exit]
TOTAL = 80


# ── HARD tier: joins, windows, sequences, medians ────────────────────────────

def h_views_by_entry(rng):
    p, q, (d1, d2) = rng.choice(PAGES[:4]), rng.choice(PAGES[4:8]), _range(rng, 30)
    return (f"How many pageviews of {p} happened in sessions whose entry page was {q}, counting pageviews between "
            f"{d1} and {d2}? Return one column: pageviews.",
            f"SELECT COUNT(*) FROM events e JOIN sessions s ON e.session_id = s.id WHERE e.type = 'pageview' "
            f"AND e.path = '{p}' AND s.entry_page = '{q}' AND {_date_cond('e.timestamp', d1, d2)}",
            False)


def h_signup_rate_by_device(rng):
    d1, d2 = _range(rng, 30)
    return (f"For sessions that started between {d1} and {d2}, what percentage included at least one 'signup' "
            "custom event, for each device? Round to 1 decimal place. Return columns: device, signup_rate (any order).",
            "SELECT s.device, ROUND(100.0 * AVG(CASE WHEN EXISTS (SELECT 1 FROM events e WHERE e.session_id = s.id "
            "AND e.type = 'custom' AND json_extract_string(e.properties, '$.name') = 'signup') THEN 1 ELSE 0 END), 1) "
            f"FROM sessions s WHERE {_date_cond('s.started_at', d1, d2)} GROUP BY s.device",
            False)


def h_pricing_then_signup(rng):
    d1, d2 = _range(rng, 45)
    return (f"How many sessions that started between {d1} and {d2} viewed /pricing and then, later in the same "
            "session, viewed /signup? Return one column: sessions.",
            "SELECT COUNT(DISTINCT a.session_id) FROM events a JOIN events b ON a.session_id = b.session_id "
            "JOIN sessions s ON s.id = a.session_id "
            "WHERE a.type = 'pageview' AND a.path = '/pricing' AND b.type = 'pageview' AND b.path = '/signup' "
            f"AND b.timestamp > a.timestamp AND {_date_cond('s.started_at', d1, d2)}",
            False)


def h_biggest_increase(rng):
    d1, d2 = _range(rng, 30)
    return (f"Between {d1} and {d2}, which day had the largest increase in sessions compared with the day before it "
            "(both days inside that range)? Return columns: date, increase.",
            "WITH d AS (SELECT CAST(started_at AS DATE) AS date, COUNT(*) AS n FROM sessions "
            f"WHERE {_date_cond('started_at', d1, d2)} GROUP BY 1), "
            "x AS (SELECT date, n - LAG(n) OVER (ORDER BY date) AS increase FROM d) "
            "SELECT date, increase FROM x WHERE increase IS NOT NULL ORDER BY increase DESC LIMIT 1",
            True)


def h_multi_day_users(rng):
    d1, d2 = _range(rng, 45)
    k = rng.choice([2, 3])
    return (f"How many users had sessions on at least {k} different days between {d1} and {d2}? "
            "Return one column: users.",
            "SELECT COUNT(*) FROM (SELECT user_id FROM sessions "
            f"WHERE {_date_cond('started_at', d1, d2)} GROUP BY user_id "
            f"HAVING COUNT(DISTINCT CAST(started_at AS DATE)) >= {k})",
            False)


def h_median_duration(rng):
    d1, d2 = _range(rng, 45)
    return (f"For sessions that started between {d1} and {d2} and had more than one pageview, what was the median "
            "duration in seconds for new versus returning visitors? Return columns: is_returning (true/false), "
            "median_duration (any order).",
            "SELECT is_returning, MEDIAN(duration) FROM sessions WHERE pageviews > 1 "
            f"AND {_date_cond('started_at', d1, d2)} GROUP BY is_returning",
            False)


def h_bounce_by_channel(rng):
    d1, d2 = _range(rng, 45)
    return (f"For sessions that started between {d1} and {d2}, what was the bounce rate (percent, 1 decimal place) "
            "for each channel? Channel is 'Search' if the referrer is 'https://www.google.com/' or "
            "'https://www.bing.com/', 'Direct' if the referrer is empty, and 'Other' otherwise. "
            "Return columns: channel, bounce_rate (any order).",
            "SELECT CASE WHEN referrer IN ('https://www.google.com/', 'https://www.bing.com/') THEN 'Search' "
            "WHEN referrer = '' OR referrer IS NULL THEN 'Direct' ELSE 'Other' END AS channel, "
            "ROUND(100.0 * AVG(CASE WHEN is_bounce THEN 1 ELSE 0 END), 1) FROM sessions "
            f"WHERE {_date_cond('started_at', d1, d2)} GROUP BY 1",
            False)


HARD_TEMPLATES = [h_views_by_entry, h_signup_rate_by_device, h_pricing_then_signup, h_biggest_increase,
                  h_multi_day_users, h_median_duration, h_bounce_by_channel]
HARD_TOTAL = 40


def _json_cell(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return float(v)


def _unique_top(con, sql) -> bool:
    """For 'which one' questions: the top row must not be tied with the next."""
    probe = con.execute(sql.replace("LIMIT 1", "LIMIT 2")).fetchall()
    return len(probe) < 2 or probe[0][-1] != probe[1][-1]


def _fill(con, rng, cases, seen, templates, target, difficulty):
    i, guard = 0, 0
    while len(cases) < target:
        guard += 1
        if guard > target * 30:
            raise RuntimeError("could not build SQL cases")
        template = templates[i % len(templates)]
        i += 1  # always move on, so one exhausted template cannot stall the build
        question, sql, ordered = template(rng)
        if question in seen:
            continue
        rows = con.execute(sql).fetchall()
        if not rows or rows == [(None,)] or rows == [(0,)]:
            continue  # an empty answer is a weak test
        if template is t_top_exit:
            # The single "most common" page must be unambiguous.
            counts = con.execute(sql.replace("SELECT exit_page", "SELECT COUNT(*)").replace("LIMIT 1", "LIMIT 2")).fetchall()
            if len(counts) > 1 and counts[0][0] == counts[1][0]:
                continue
        if template is h_biggest_increase and not _unique_top(con, sql):
            continue
        seen.add(question)
        expected = [[_json_cell(c) for c in row] for row in rows]
        cases.append({
            "id": f"sql_{len(cases) + 1:03d}",
            "group": "sql",
            "subgroup": template.__name__.removeprefix("t_").removeprefix("h_")
            if difficulty == "standard" else "hard_" + template.__name__.removeprefix("h_"),
            "difficulty": difficulty,
            "question": question,
            "reference_sql": sql,
            # Unordered answers are stored sorted, so rebuilds are byte-identical.
            "expected": expected if ordered else sorted(expected, key=lambda r: json.dumps(r)),
            "ordered": ordered,
        })


def build(con, seed: int = 19) -> list[dict]:
    rng = random.Random(seed)
    cases, seen = [], set()
    _fill(con, rng, cases, seen, TEMPLATES, TOTAL, "standard")
    _fill(con, rng, cases, seen, HARD_TEMPLATES, TOTAL + HARD_TOTAL, "hard")
    return cases
