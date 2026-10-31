"""Forecast error metrics. Error = forecast - actual (positive = forecast too high = wind shortfall)."""
import math
import statistics
from collections import defaultdict

from data import UK

MAPE_MIN_ACTUAL = 1000  # MW; below this, percentage errors blow up


def pct(xs, p):
    """p-th percentile (1-99), linear interpolation."""
    return statistics.quantiles(xs, n=100, method="inclusive")[p - 1] if len(xs) > 1 else xs[0]


def stats(rows):
    rows = [r for r in rows if r["forecast"] is not None]
    if not rows:
        return {"n": 0}
    err = [r["forecast"] - r["actual"] for r in rows]
    ab = [abs(e) for e in err]
    mape = [abs(e) / r["actual"] for e, r in zip(err, rows) if r["actual"] >= MAPE_MIN_ACTUAL]
    ratio = [r["actual"] / r["forecast"] for r in rows if r["forecast"] > 0]
    return {
        "n": len(rows),
        "mae": statistics.fmean(ab),
        "rmse": math.sqrt(statistics.fmean(e * e for e in err)),
        "bias": statistics.fmean(err),
        "median_ae": statistics.median(ab),
        "p90_ae": pct(ab, 90),
        "p99_ae": pct(ab, 99),
        "mape": statistics.fmean(mape) * 100 if mape else None,
        # Planning: in 90% of hours actual >= forecast * ratio_p10, and shortfall <= shortfall_p90 MW.
        "ratio_p10": pct(ratio, 10) if ratio else None,
        "shortfall_p90": pct(err, 90),
        "mean_actual": statistics.fmean(r["actual"] for r in rows),
        "mean_forecast": statistics.fmean(r["forecast"] for r in rows),
    }


def by_hour(rows):
    """MAE and bias per UK hour of day."""
    groups = defaultdict(list)
    for r in rows:
        if r["forecast"] is not None:
            groups[r["time"].astimezone(UK).hour].append(r["forecast"] - r["actual"])
    return [{"hour": h, "mae": statistics.fmean(map(abs, e)), "bias": statistics.fmean(e), "n": len(e)}
            for h, e in sorted(groups.items())]


if __name__ == "__main__":
    from datetime import datetime, timezone
    t = datetime(2026, 1, 2, tzinfo=timezone.utc)
    rows = [{"time": t, "actual": a, "forecast": f} for a, f in [(1000, 1100), (2000, 1800), (3000, 3000), (4000, None)]]
    s = stats(rows)
    assert s["n"] == 3 and s["mae"] == 100 and abs(s["bias"] - (-100 / 3)) < 1e-9
    assert abs(s["rmse"] - math.sqrt(50000 / 3)) < 1e-9
    assert by_hour(rows) == [{"hour": 0, "mae": 100, "bias": -100 / 3, "n": 3}]
    print("ok")
