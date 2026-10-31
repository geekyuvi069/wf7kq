"""Run: python backend/test_data.py  (pytest also collects it)."""
from datetime import date, datetime, time, timezone

from data import cutoff, latest, parse, series

UTC = timezone.utc


def test_cutoff_uses_uk_date_and_time():
    # January: GMT == UTC, decision 09:20 on D-1
    assert cutoff(parse("2026-01-10T15:00:00Z")) == datetime(2026, 1, 9, 9, 20, tzinfo=UTC)
    # July: 23:30Z is 00:30 BST next day, so D-1 is 1 July; 09:20 BST == 08:20Z
    assert cutoff(parse("2026-07-01T23:30:00Z")) == datetime(2026, 7, 1, 8, 20, tzinfo=UTC)
    assert cutoff(parse("2026-01-10T15:00:00Z"), horizon=6) == datetime(2026, 1, 10, 9, tzinfo=UTC)


def test_latest_picks_last_publish_at_or_before_cutoff():
    pubs = [parse(p) for p in ("2026-01-09T04:30:00Z", "2026-01-09T07:30:00Z", "2026-01-09T09:30:00Z")]
    gens = [100.0, 200.0, 300.0]
    assert latest(pubs, gens, datetime(2026, 1, 9, 9, 20, tzinfo=UTC)) == (pubs[1], 200.0)
    assert latest(pubs, gens, pubs[2]) == (pubs[2], 300.0)  # inclusive
    assert latest(pubs, gens, datetime(2026, 1, 1, tzinfo=UTC)) == (None, None)


def test_series_on_real_data():
    rows = series(date(2026, 1, 2), date(2026, 2, 1))
    assert len(rows) == 31 * 24
    assert all(r["forecast"] is not None for r in rows)
    # 09:20 decision: 07:30 publish is the last one before gate closure
    assert {r["publishTime"].time() for r in rows} == {time(7, 30)}
    h = series(date(2026, 1, 2), date(2026, 2, 1), horizon=1)
    assert all(r["publishTime"] <= r["time"] for r in h)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
