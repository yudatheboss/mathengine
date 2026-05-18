# USD/JPY Engine — Live Mode Setup

You now have four files. Here's what each does and how to wire them together.

## The files

| File | Purpose |
|---|---|
| `usdjpy-engine.html` | The dashboard. Open in browser. Sim mode works immediately. Live mode needs Supabase config. |
| `fetch_data.py` | Pulls real data from FRED + Yahoo. Writes to Supabase. |
| `fetch-data.yml` | GitHub Actions config. Runs `fetch_data.py` every 15 minutes automatically. |
| `README.md` | This file. |

## Setup walkthrough — about 25 minutes total

### Step 1 — Supabase (10 min)

1. Sign up at **supabase.com**. Free.
2. Create project. Name it `usdjpy-engine`. Region: any close to you.
3. Wait ~2 min for provisioning.
4. Go to **SQL Editor** → New query → paste and run:

```sql
create table market_snapshots (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  us_2y numeric(5,3) not null,
  jgb_2y numeric(5,3) not null,
  vix numeric(5,2) not null,
  oil_wti numeric(6,2) not null,
  usdjpy_spot numeric(7,3) not null,
  positioning_pct numeric(5,2),
  source text default 'manual'
);
create index on market_snapshots (created_at desc);

alter table market_snapshots enable row level security;
create policy "anyone can read" on market_snapshots for select using (true);

insert into market_snapshots (us_2y, jgb_2y, vix, oil_wti, usdjpy_spot, positioning_pct)
values (4.50, 0.80, 14.00, 78.00, 150.00, 50);
```

5. Go to **Project Settings → API**. You need three values:
   - **Project URL** — paste into the HTML dashboard Live config
   - **anon public key** — paste into the HTML dashboard Live config
   - **service_role secret** — paste into GitHub secrets (NEVER put in HTML)

### Step 2 — FRED API key (2 min)

1. Go to **fred.stlouisfed.org/docs/api/api_key.html**
2. Sign up, request key. Instant approval.
3. Save the key for step 4.

### Step 3 — Wire HTML to Supabase (1 min)

1. Open `usdjpy-engine.html` in your browser (double-click the file).
2. Scroll to bottom. Click "show/hide" on Supabase connection.
3. Paste your **Project URL** and **anon public key** (not service_role).
4. Click "Save & test connection". You should see "Connected."
5. Click the **Live** toggle at the top. Sliders snap to the starter row values.
6. Sim mode still works exactly as before — toggle back any time.

You now have live mode reading data. Next step makes the data update automatically.

### Step 4 — Auto-fetcher via GitHub Actions (12 min)

1. Create a free GitHub account if needed.
2. Create a **new repository**. Name it `usdjpy-fetcher`. Make it **private**. Initialize empty.
3. Add two files via the GitHub web UI (Add file → Create new file):
   - **Filename:** `fetch_data.py` — paste contents from `fetch_data.py` in this folder. Commit.
   - **Filename:** `.github/workflows/fetch-data.yml` — type the path exactly with slashes. Paste contents from `fetch-data.yml`. Commit.
4. Add secrets. Repo page → **Settings → Secrets and variables → Actions → New repository secret**. Add three:
   - `FRED_API_KEY` — your FRED key
   - `SUPABASE_URL` — your project URL (same one in HTML)
   - `SUPABASE_SERVICE_KEY` — your **service_role** key (NOT anon — they're different)
5. Test it. **Actions** tab → "Fetch USD/JPY data" → **Run workflow** button → Run.
6. Wait ~30 sec. Green check = worked. Go to Supabase **Table Editor → market_snapshots** — you should see a new row with real values.

From now on it runs every 15 minutes automatically.

## What live mode does for you

- Spot price = real USD/JPY
- Fair value = computed from real US 2Y, your manual JGB 2Y, real oil
- Divergence = the actual current edge in the market
- Regime label = based on real positioning + real VIX + real divergence

The dashed fair value line is real. The gap between solid and dashed is real. When it stretches red, that's a real setup.

## Per-slider override (the "what if" superpower)

In live mode, each slider has a small 🔒 icon. Click to unlock → "OVERRIDE" tag appears → that slider becomes interactive while everything else stays live.

Use cases:
- BoJ meeting tomorrow — unlock JGB 2Y, bump +0.25 → see where fair value moves
- CPI tonight — unlock US 2Y, bump +0.15 → simulate a hot print
- Imagining a vol spike — unlock VIX, push to 30 → see regime label flip

Lock it back to return that input to live data.

## Manual inputs you still update by hand

Two values have no reliable free API:
- **JGB 2Y** — edit `JGB_2Y_MANUAL` constant in `fetch_data.py` once a day. Source: investing.com/rates-bonds/japan-2-year-bond-yield
- **Positioning** — edit `POSITIONING_PCT_MANUAL`. Update weekly when CFTC COT publishes Friday. 0 = neutral, 100 = extreme short JPY. Source: cftc.gov or barchart.com COT report

Edit, commit. Next workflow run uses the new values.

## When something breaks

| Symptom | Check |
|---|---|
| Live mode says "no data yet" | Supabase config saved? URL and anon key correct? |
| Connection failed | RLS policy created (the `create policy` SQL)? |
| GitHub Action fails | Click failed run → check logs. Usually missing secret or wrong key. |
| Values look wrong | Check Supabase table — what was actually written? FRED lags weekends/holidays. |
| Dashed line missing | Hard refresh browser (Ctrl+Shift+R). Should always be visible. |

## Next steps from here

When this is running smoothly for a week, ping me. We add:
1. **History view** — last 24h chart in live mode (not just latest point)
2. **Trade journal** — log entries with regime snapshot, see win rate by regime
3. **News input** — type a headline, AI projects fair value impact
4. **Alerts** — when divergence exceeds 1.5σ or regime flips

Each one additive. Engine stays the same.
