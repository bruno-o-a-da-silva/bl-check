"""Command line.

  python -m bl_check check examples/shipments.json --now 2026-03-05T08:00
  python -m bl_check simulate [--seed 11] [--rate 0.03] [--per-day 3]
  python -m bl_check serve [--port 8000]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .engine import load, rank, run
from .models import Shipment
from .simulate import compare


def check(path: str, now: datetime, rules: str | None) -> list[str]:
    rs = load(Path(rules).read_text() if rules else None)
    ships = [Shipment.model_validate(x) for x in json.loads(Path(path).read_text())]
    found = rank([m for s in ships for m in run(s, rs)], now)
    lines = [f"{len(found)} mismatches in {len(ships)} bookings, nearest cut-off first"]
    for m in found:
        h = m.hours_left(now)
        when = f"{h:5.1f} h left" if h >= 0 else "  cut-off missed"
        lines.append(f"  {when}  {m.booking}  {m.rule:<10} {m.detail}")
    return lines


def simulate(seed: int, rate: float, per_day: int) -> list[str]:
    r = compare(seed=seed, rate=rate, per_day=per_day)
    n = r["none"]
    lines = [f"synthetic: {n.bookings} bookings, seed {seed}, each of 7 error types injected "
             f"with probability {rate:.0%}; {n.with_errors} bookings have at least one error, "
             f"{n.not_catchable} only errors that every document repeats",
             f"one analyst fixes {per_day} bookings a day",
             f"{'':22}{'amendments':>11}{'rollovers':>10}{'cost':>12}"]
    for name, key in (("no check", "none"), ("check, FIFO review", "fifo"),
                      ("check, ranked review", "ranked")):
        o = r[key]  # type: ignore[index]
        lines.append(f"{name:22}{o.amendments:>11}{o.rollovers:>10}{o.cost:>12,.2f}")
    best = r["ranked"]
    lines.append(f"avoided vs no check: {n.amendments - best.amendments} amendments, "
                 f"{n.rollovers - best.rollovers} rollovers, {n.cost - best.cost:,.2f}")
    return lines


def main(argv: list[str] | None = None) -> str:
    ap = argparse.ArgumentParser(prog="bl_check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--now", type=datetime.fromisoformat, required=True)
    c.add_argument("--rules")
    s = sub.add_parser("simulate")
    s.add_argument("--seed", type=int, default=11)
    s.add_argument("--rate", type=float, default=0.03)
    s.add_argument("--per-day", type=int, default=3)
    v = sub.add_parser("serve")
    v.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        import uvicorn

        uvicorn.run("bl_check.api:app", host="127.0.0.1", port=a.port)
        return ""
    lines = check(a.file, a.now, a.rules) if a.cmd == "check" else \
        simulate(a.seed, a.rate, a.per_day)
    out = "\n".join(lines)
    print(out)
    return out


if __name__ == "__main__":  # pragma: no cover
    main()
