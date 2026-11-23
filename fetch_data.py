"""
fetch_data.py - OPTIONAL. Rebuilds the data files from the original sources.

You do NOT need this to reproduce the results: the frozen snapshot in data/
is what every number in the memo comes from. Run this only to check the
snapshot against the sources, or to prepare next year's review.

    python fetch_data.py            # writes data/refresh/..., compares returns
    python fetch_data.py --replace  # also overwrites the frozen snapshot (careful)

Sources: Yahoo Finance chart API (daily Adj Close -> last trading day of each
month) and ALFRED (one GS2 vintage per review date). No API key is needed.
"""
import argparse
import csv
import hashlib
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REFRESH = DATA / "refresh"
TICKERS = ["BIL", "IEF", "LQD", "VT"]
NY_OFFSET_HOURS = -5  # bar timestamps are market open (09:30 New York); any offset in
                      # -4..-5 maps them to the right calendar day


def get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (FIN43900 student project)"})
    with urlopen(req, timeout=60) as r:
        return r.read()


def month_ends_from_chart(payload: bytes, last_complete_month: str) -> dict:
    """Yahoo chart JSON (daily bars) -> {YYYY-MM: (trading_date, adjclose)}."""
    data = json.loads(payload)
    if data["chart"].get("error"):
        raise RuntimeError(data["chart"]["error"])
    res = data["chart"]["result"][0]
    out = {}
    for ts, adj in zip(res["timestamp"], res["indicators"]["adjclose"][0]["adjclose"]):
        if adj is None:
            continue
        day = (datetime.fromtimestamp(ts, timezone.utc) + timedelta(hours=NY_OFFSET_HOURS)).date()
        key = day.strftime("%Y-%m")
        if key <= last_complete_month:
            out[key] = (day.isoformat(), adj)       # later days overwrite -> last trading day
    return out


def fetch_prices(last_complete_month: str) -> tuple[list, dict]:
    p2 = int(datetime.now(timezone.utc).timestamp())
    series, meta = {}, {}
    for t in TICKERS:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=1167609600"
               f"&period2={p2}&interval=1d&events=div%2Csplits")
        payload = get(url)
        series[t] = month_ends_from_chart(payload, last_complete_month)
        meta[t] = {"url": url, "sha256": hashlib.sha256(payload).hexdigest(),
                   "retrieved_utc": datetime.now(timezone.utc).isoformat()}
        print(f"{t}: {len(series[t])} month-ends", flush=True)
    months = sorted(m for m in set.intersection(*(set(series[t]) for t in TICKERS)) if m >= "2008-06")
    rows = [[series["VT"][m][0]] + [repr(series[t][m][1]) for t in TICKERS] for m in months]
    return rows, meta


def fetch_gs2(review_dates: list) -> list:
    rows = []
    for vd in review_dates:
        url = f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=GS2&vintage_date={vd}"
        payload = get(url)
        obs = [r for r in csv.reader(io.StringIO(payload.decode())) if len(r) == 2][1:]
        obs = [r for r in obs if r[1] not in (".", "")]
        last = obs[-1]
        rows.append([vd, last[0][:7], last[1], len(obs), "", hashlib.sha256(payload).hexdigest(), url])
        print(f"GS2 {vd}: {last[0][:7]} = {last[1]}", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true", help="overwrite the frozen snapshot")
    a = ap.parse_args()
    today = date.today()
    last_complete = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    REFRESH.mkdir(parents=True, exist_ok=True)
    rows, meta = fetch_prices(last_complete)
    with (REFRESH / "prices_monthly.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date"] + TICKERS)
        w.writerows(rows)
    reviews = [f"{y}-09-30" for y in range(2009, today.year + 1) if date(y, 9, 30) <= today]
    g = fetch_gs2(reviews)
    with (REFRESH / "gs2_vintages.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["vintage_date", "last_month_measured", "gs2_percent", "observations_in_vintage",
                    "value_in_2026-11-19_vintage", "response_sha256", "source_url"])
        w.writerows(g)
    (REFRESH / "refresh_provenance.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    # compare monthly RETURNS with the frozen snapshot (levels change at every distribution)
    sys.path.insert(0, str(ROOT))
    import engine as e
    old = e.monthly_returns(e.load_prices(DATA / "prices_monthly.csv"))
    new = e.monthly_returns(e.load_prices(REFRESH / "prices_monthly.csv"))
    common = old.index.intersection(new.index)
    diff = (old.loc[common] - new.loc[common]).abs().max().max() * 100
    print(f"Largest monthly-return difference vs frozen snapshot over {len(common)} months: "
          f"{diff:.4f} percentage points")
    if a.replace:
        (DATA / "prices_monthly.csv").write_bytes((REFRESH / "prices_monthly.csv").read_bytes())
        (DATA / "gs2_vintages.csv").write_bytes((REFRESH / "gs2_vintages.csv").read_bytes())
        print("Frozen snapshot REPLACED. Re-run python run_analysis.py and update the memo.")


if __name__ == "__main__":
    main()
