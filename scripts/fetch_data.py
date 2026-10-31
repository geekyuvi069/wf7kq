"""Fetch Jan-2026 GB wind actuals (FUELHH) and forecasts (WINDFOR) from Elexon into data/*.csv.

Run: python scripts/fetch_data.py
"""
import csv
import json
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA = Path(__file__).resolve().parent.parent / "data"
# Decisions on 2026-01-01..31 -> delivery 2026-01-02..2026-02-01.
# Forecasts from a few days before the first decision; actuals from the day before first delivery.
FC_FROM, FC_TO = date(2025, 12, 29), date(2026, 2, 2)
ACT_FROM, ACT_TO = date(2026, 1, 1), date(2026, 2, 2)


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def chunks(start, end, days=7):
    while start < end:
        yield start, min(start + timedelta(days=days), end)
        start += timedelta(days=days)


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def fetch_actuals():
    rows = {}
    for a, b in chunks(ACT_FROM, ACT_TO):
        # settlementDateTo is inclusive, so stop the day before the next chunk.
        url = (f"{BASE}/FUELHH/stream?fuelType=WIND"
               f"&settlementDateFrom={a}&settlementDateTo={b - timedelta(days=1)}")
        for r in get(url):
            rows[r["startTime"]] = r["generation"]
    return sorted(rows.items())


def fetch_forecasts():
    rows = {}
    for a, b in chunks(FC_FROM, FC_TO):
        url = (f"{BASE}/WINDFOR/stream"
               f"?publishDateTimeFrom={a}T00:00:00Z&publishDateTimeTo={b}T00:00:00Z")
        for r in get(url):
            rows[(r["startTime"], r["publishTime"])] = r["generation"]
    return sorted((s, p, g) for (s, p), g in rows.items())


def check(actuals, forecasts):
    ts = [parse(t) for t, _ in actuals]
    gaps = [(a, b) for a, b in zip(ts, ts[1:]) if b - a != timedelta(minutes=30)]
    print(f"actuals: {len(actuals)} rows, {ts[0]} .. {ts[-1]}, gaps: {len(gaps)}")
    for a, b in gaps[:10]:
        print(f"  gap {a} -> {b}")

    pt = sorted({parse(p) for _, p, _ in forecasts})
    big = [(a, b) for a, b in zip(pt, pt[1:]) if b - a > timedelta(hours=3)]
    print(f"forecasts: {len(forecasts)} rows, {len(pt)} publishes, {pt[0]} .. {pt[-1]}, publish gaps >3h: {len(big)}")
    for a, b in big[:10]:
        print(f"  gap {a} -> {b}")

    neg = sum(g < 0 for _, g in actuals) + sum(g < 0 for *_, g in forecasts)
    assert neg == 0, f"{neg} negative generation values"
    assert ts[0] <= datetime(2026, 1, 2, tzinfo=timezone.utc), "actuals start too late"
    assert ts[-1] >= datetime(2026, 2, 1, 23, tzinfo=timezone.utc), "actuals end too early"


def main():
    DATA.mkdir(exist_ok=True)
    actuals, forecasts = fetch_actuals(), fetch_forecasts()
    with open(DATA / "actuals.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["startTime", "generation"])
        w.writerows(actuals)
    with open(DATA / "forecasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["startTime", "publishTime", "generation"])
        w.writerows(forecasts)
    check(actuals, forecasts)


if __name__ == "__main__":
    main()
