"""Local HTTP API. Run `python -m bl_check serve`, then open http://127.0.0.1:8000/docs."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from .engine import load, rank, run
from .models import Shipment

RULES = load()
app = FastAPI(title="bl-check", version="0.0.1",
              description="Cross-field checks between booking, VGM and B/L draft, ranked by "
                          "cut-off. Checks consistency between documents, not the truth.")


class MismatchOut(BaseModel):
    booking: str
    rule: str
    document: str
    severity: int
    detail: str
    cutoff: datetime
    hours_left: float


class RuleOut(BaseModel):
    id: str
    check: str
    document: str
    severity: int


@app.get("/rules")
def rules() -> list[RuleOut]:
    return [RuleOut(id=r.id, check=r.check, document=r.document, severity=r.severity)
            for r in RULES.rules]


@app.post("/check")
def check(shipments: list[Shipment], now: datetime) -> list[MismatchOut]:
    """Mismatches of every shipment sent, nearest cut-off first."""
    found = [m for s in shipments for m in run(s, RULES)]
    return [MismatchOut(booking=m.booking, rule=m.rule, document=m.document,
                        severity=m.severity, detail=m.detail, cutoff=m.cutoff,
                        hours_left=round(m.hours_left(now), 1)) for m in rank(found, now)]
