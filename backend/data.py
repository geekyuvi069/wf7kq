"""Load committed Elexon CSVs and pick the forecast a buyer could actually have seen."""
import bisect
import csv
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parent.parent / "data"
UK = ZoneInfo("Europe/London")
# EPEX GB day-ahead auction gate closure (N2EX closes later, 09:50); buyer must be done by the first.
DEFAULT_DECISION = time(9, 20)


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


@lru_cache(maxsize=1)
def load():
    """-> (actuals {startTime: MW}, forecasts {startTime: ([publishTime...], [MW...])} sorted by publish)."""
    with open(DATA / "actuals.csv") as f:
        actuals = {parse(r["startTime"]): float(r["generation"]) for r in csv.DictReader(f)}
    fc = {}
    with open(DATA / "forecasts.csv") as f:
        for r in csv.DictReader(f):  # file is sorted by (startTime, publishTime)
            pubs, gens = fc.setdefault(parse(r["startTime"]), ([], []))
            pubs.append(parse(r["publishTime"]))
            gens.append(float(r["generation"]))
    return actuals, fc


def cutoff(start, decision=None, horizon=None):
    """Latest publishTime usable for target `start`.

    decision: local UK time on D-1, where D is the UK calendar date of `start`.
    horizon: hours before `start` (overrides decision).
    """
    if horizon is not None:
        return start - timedelta(hours=horizon)
    # ponytail: D = UK calendar day; GB auction "day" actually runs 23:00-23:00 UK, refine if traders care.
    d = start.astimezone(UK).date() - timedelta(days=1)
    return datetime.combine(d, decision or DEFAULT_DECISION, UK)


def latest(pubs, gens, cut):
    """Latest forecast with publishTime <= cut."""
    i = bisect.bisect_right(pubs, cut)
    return (pubs[i - 1], gens[i - 1]) if i else (None, None)


def series(start: date, end: date, decision=None, horizon=None):
    """Hourly rows for UK delivery dates start..end inclusive (forecasts are hourly, so :30 actuals are skipped)."""
    actuals, fc = load()
    out = []
    for t in sorted(actuals):
        if not start <= t.astimezone(UK).date() <= end or t not in fc:
            continue
        # min(..., t): never use a forecast published after its own target hour
        pub, gen = latest(*fc[t], min(cutoff(t, decision, horizon), t))
        out.append({"time": t, "actual": actuals[t], "forecast": gen, "publishTime": pub})
    return out
