# GB Wind Forecast Monitor

A web app for a UK utility's day-ahead power buying team. For every delivery hour it shows the national wind
forecast that was **actually available when the purchase decision had to be made** (D-1, before the
day-ahead auction gate closes), compares it with what the wind really generated, and turns the error into a
buying margin: how much of the forecast you can count on, and how much extra to buy to be covered 9 hours in 10.

Scope: GB national wind generation, Elexon BMRS data, purchase decisions made in January 2026
(delivery days 2 Jan to 1 Feb 2026).

**Live app:** _add Vercel URL here_

## What it shows

- **Actual vs forecast chart** for the chosen delivery days, plus a table of every hour.
- **Forecast used**, in one of two modes:
  - *At decision time* (default): for each hour of day D, the latest forecast published at or before the
    decision time on D-1. The default is 09:20 UK, the EPEX GB day-ahead auction gate closure (N2EX closes at 09:50).
  - *Fixed horizon*: the latest forecast published at least H hours before each delivery hour.
- **Metric cards**: "wind you can count on" (P10 of actual / forecast), extra to buy for 90% cover
  (P90 of forecast − actual), bias, MAE, RMSE, MAPE, median / P90 / P99 absolute error.
- **Error by hour of day** and **error vs forecast horizon** (1 to 48 h).

Error is defined as `forecast − actual`, so a positive error means the wind came in below forecast and the shortfall has to be bought.

## Data

| Dataset | Endpoint | Used fields |
|---|---|---|
| Actual generation (FUELHH, `fuelType=WIND`) | `https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream` | `startTime`, `generation` (MW, half-hourly) |
| Wind forecast (WINDFOR) | `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream` | `startTime`, `publishTime`, `generation` (MW, hourly) |

The data is historical and fixed, so it is fetched once and committed as CSV in `data/`. The app never depends on
Elexon being up. Forecasts are hourly, so actuals are compared on the hour.

## Repository layout

```
api/index.py          Vercel serverless entry; re-exports the FastAPI app
backend/app.py        FastAPI: /api/series, /api/stats, /api/horizon; serves the React build in Docker
backend/data.py       Loads the CSVs; picks the latest forecast published before the decision cutoff
backend/metrics.py    Error metrics (MAE, RMSE, bias, percentiles, MAPE, by hour of day)
backend/test_*.py     Tests for the cutoff/selection logic and the API
scripts/fetch_data.py Refreshes data/*.csv from Elexon and sanity-checks counts, gaps and negatives
data/                 actuals.csv, forecasts.csv (committed snapshot)
frontend/             Vite + React + Recharts single-page UI
Dockerfile            Multi-stage: builds the frontend, then one FastAPI container serves API + UI
docker-compose.yml    `docker compose up` on port 8000
vercel.json           Vercel build (static frontend) + Python function for /api
```

## API

All endpoints take `start` and `end` (delivery dates, `YYYY-MM-DD`), plus either `decision` (`HH:MM` UK time on
D-1) or `horizon` (hours, overrides `decision`).

- `GET /api/series` → `[{time, actual, forecast, publishTime}]`
- `GET /api/stats` → metrics plus `by_hour`
- `GET /api/horizon?max_h=48` → MAE / bias / P90 for each horizon from 1 to `max_h` hours

## Run it

**Docker (one command):**
```bash
docker compose up --build      # http://localhost:8000
```

**Local dev:**
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --app-dir backend --reload       # API on :8000
cd frontend && npm ci && npm run dev                       # UI on :5173, proxies /api to :8000
```

**Tests:**
```bash
cd backend
../.venv/bin/python test_data.py && ../.venv/bin/python test_app.py && ../.venv/bin/python metrics.py
```
(`pytest` collects the same tests if installed.)

**Refresh data:** `python3 scripts/fetch_data.py`

**Deploy:** `npx vercel --prod` from the repo root (uses `vercel.json`).

## Design notes

- **No look-ahead.** Forecast selection is a binary search over each hour's sorted publish times. Only forecasts
  with `publishTime <= cutoff` (and never after the delivery hour itself) are used.
- **Time zones.** The decision time is UK local time, converted with `zoneinfo`, so it stays correct across GMT/BST.
- **Light dependencies.** The backend uses the standard library plus FastAPI, with no pandas, so the Vercel function stays small and starts fast.
- **Known simplification.** Day D is the UK calendar date. The GB day-ahead auction day actually runs 23:00 to 23:00 UK, which only affects the first hour of each day.

## AI tools

AI coding assistants (Claude Code) were used during development, for research, code drafting and review. All design decisions and results were checked by hand and with the tests above.
