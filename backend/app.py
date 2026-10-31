"""API (+ built frontend if present): uvicorn app:app --app-dir backend"""
from datetime import date, time
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

import metrics
from data import DEFAULT_DECISION, series

app = FastAPI(title="GB wind forecast monitor")

# Delivery days for January-2026 decisions.
Start = Annotated[date, Query()]
End = Annotated[date, Query()]
Decision = Annotated[time, Query(description="HH:MM UK time on D-1")]
Horizon = Annotated[float | None, Query(ge=0, le=72, description="hours before target; overrides decision")]
START, END = date(2026, 1, 2), date(2026, 2, 1)


def _rows(start, end, decision, horizon):
    if start > end:
        raise HTTPException(400, "start must be <= end")
    return series(start, end, decision, horizon)


@app.get("/api/series")
def get_series(start: Start = START, end: End = END, decision: Decision = DEFAULT_DECISION, horizon: Horizon = None):
    return [{"time": r["time"].isoformat(), "actual": r["actual"], "forecast": r["forecast"],
             "publishTime": r["publishTime"] and r["publishTime"].isoformat()}
            for r in _rows(start, end, decision, horizon)]


@app.get("/api/stats")
def get_stats(start: Start = START, end: End = END, decision: Decision = DEFAULT_DECISION, horizon: Horizon = None):
    rows = _rows(start, end, decision, horizon)
    return {**metrics.stats(rows), "by_hour": metrics.by_hour(rows)}


@app.get("/api/horizon")
def get_horizon(start: Start = START, end: End = END, max_h: Annotated[int, Query(ge=1, le=72)] = 48):
    """Error vs forecast horizon, 1..max_h hours."""
    out = []
    for h in range(1, max_h + 1):
        s = metrics.stats(_rows(start, end, None, h))
        out.append({"horizon": h, "n": s["n"], "mae": s.get("mae"), "bias": s.get("bias"), "p90_ae": s.get("p90_ae")})
    return out


# Docker serves the React build from here; on Vercel the static files are served by Vercel instead.
DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
