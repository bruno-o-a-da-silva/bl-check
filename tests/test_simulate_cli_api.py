import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bl_check import __main__ as cli
from bl_check.api import app
from bl_check.simulate import compare
from bl_check.synthetic import cases

EXAMPLE = str(Path(__file__).parent.parent / "examples" / "shipments.json")


def test_cases_are_seeded_and_rate_zero_is_clean() -> None:
    assert cases(20, 1, 0.1) == cases(20, 1, 0.1)
    r = compare(n=50, seed=1, rate=0.0)
    assert all(o.with_errors == 0 and o.cost == Decimal(0) for o in r.values())


def test_headline_run_is_stable() -> None:
    out = cli.main(["simulate", "--seed", "11", "--rate", "0.03", "--per-day", "3"])
    assert "113 bookings have at least one error, 16 only errors" in out
    assert "no check                       98        19   82,100.00" in out
    assert "check, FIFO review             38         2   21,100.00" in out
    assert "check, ranked review           36         0   16,200.00" in out
    assert "avoided vs no check: 62 amendments, 19 rollovers, 65,900.00" in out


def test_check_command(tmp_path: Path) -> None:
    out = cli.main(["check", EXAMPLE, "--now", "2026-03-03T08:00"])
    assert out.startswith("5 mismatches in 3 bookings")
    assert "BK00002  VGM-SUM" in out
    rules = json.loads((Path(cli.__file__).parent / "rules.json").read_text())
    rules["rules"] = [r for r in rules["rules"] if r["id"] == "VGM-SUM"]
    f = tmp_path / "r.json"
    f.write_text(json.dumps(rules))
    late = cli.main(["check", EXAMPLE, "--now", "2026-03-10T08:00", "--rules", str(f)])
    assert late.splitlines()[1].startswith("    cut-off missed  BK00002  VGM-SUM")


def test_serve_starts_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: seen.update(app=app, **kw))
    assert cli.main(["serve", "--port", "8123"]) == ""
    assert seen == {"app": "bl_check.api:app", "host": "127.0.0.1", "port": 8123}


def test_http_api() -> None:
    c = TestClient(app)
    assert len(c.get("/rules").json()) == 10
    body = json.loads(Path(EXAMPLE).read_text())
    r = c.post("/check", params={"now": "2026-03-03T08:00:00"}, json=body)
    assert r.status_code == 200
    got = r.json()
    assert [m["rule"] for m in got][:2] == ["VGM-SUM", "BL-DIGIT"]
    assert got[0]["hours_left"] == 82.0
    assert c.post("/check", params={"now": "2026-03-03T08:00:00"},
                  json=[{"booking": {}}]).status_code == 422
    assert "/check" in c.get("/openapi.json").json()["paths"]
