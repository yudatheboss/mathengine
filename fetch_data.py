"""
USD/JPY data fetcher.
Pulls US 2Y, VIX, WTI from FRED, USD/JPY spot from Yahoo Finance,
then writes a new row to Supabase.

Run via GitHub Actions cron every 5 minutes.
Requires environment variables:
  FRED_API_KEY = (os.environ.get("FRED_API_KEY") or "").strip()
  SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
  SUPABASE_SERVICE_KEY = (os.environ.get("SUPABASE_SERVICE_KEY") or "").strip()
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

FRED_API_KEY = os.environ.get("FRED_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Manual values you update by hand. Edit these and commit when needed.
# JGB 2Y has no free reliable API. Update from Bloomberg/Investing.com once a day.
JGB_2Y_MANUAL = 0.85  # percent
POSITIONING_PCT_MANUAL = 65  # 0-100, your read of CFTC COT

if not all([FRED_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY]):
    print("ERROR: missing env vars FRED_API_KEY, SUPABASE_URL, or SUPABASE_SERVICE_KEY")
    sys.exit(1)


def fetch_fred(series_id: str) -> float:
    """Get the most recent observation for a FRED series."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,  # fetch a few in case latest is missing
    }
    url = f"https://api.stlouisfed.org/fred/series/observations?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
    for obs in data["observations"]:
        v = obs["value"]
        if v != ".":
            return float(v)
    raise ValueError(f"No usable observation for {series_id}")


def fetch_yahoo_usdjpy() -> float:
    """Get latest USD/JPY from Yahoo Finance chart endpoint."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/JPY=X?interval=5m&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    result = data["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    # walk back to find the latest non-null close
    for v in reversed(closes):
        if v is not None:
            return float(v)
    raise ValueError("No usable USD/JPY close")


def write_supabase(row: dict) -> None:
    """Insert a row into market_snapshots."""
    url = f"{SUPABASE_URL}/rest/v1/market_snapshots"
    body = json.dumps(row).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        if r.status not in (200, 201):
            raise RuntimeError(f"Supabase insert failed: {r.status} {r.read()}")


def main():
    print(f"[{datetime.utcnow().isoformat()}] fetching...")
    us_2y = fetch_fred("DGS2")
    vix = fetch_fred("VIXCLS")
    oil = fetch_fred("DCOILWTICO")
    usdjpy = fetch_yahoo_usdjpy()

    row = {
        "us_2y": round(us_2y, 3),
        "jgb_2y": round(JGB_2Y_MANUAL, 3),
        "vix": round(vix, 2),
        "oil_wti": round(oil, 2),
        "usdjpy_spot": round(usdjpy, 3),
        "positioning_pct": POSITIONING_PCT_MANUAL,
        "source": "github-actions",
    }
    print(f"writing: {row}")
    write_supabase(row)
    print("OK")


if __name__ == "__main__":
    main()
