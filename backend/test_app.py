"""Run: .venv/bin/python backend/test_app.py  (pytest also collects it)."""
from fastapi.testclient import TestClient

from app import app

c = TestClient(app)


def test_endpoints():
    s = c.get("/api/series").json()
    assert len(s) == 744 and s[0]["publishTime"].startswith("2026-01-01T07:30")
    st = c.get("/api/stats", params={"decision": "09:50"}).json()
    assert st["n"] == 744 and len(st["by_hour"]) == 24
    assert c.get("/api/stats", params={"horizon": 4}).json()["n"] == 744
    hz = c.get("/api/horizon", params={"max_h": 6}).json()
    assert [r["horizon"] for r in hz] == [1, 2, 3, 4, 5, 6]
    assert c.get("/api/series", params={"start": "2026-01-10", "end": "2026-01-09"}).status_code == 400
    assert c.get("/api/series", params={"horizon": 999}).status_code == 422


if __name__ == "__main__":
    test_endpoints()
    print("ok")
