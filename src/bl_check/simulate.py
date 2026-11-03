"""Measure amendments and rollovers with and without the check, and with two review orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from .engine import Mismatch, RuleSet, load, rank, run
from .synthetic import START, VGM_ERRORS, Case, cases

AMENDMENT = Decimal("450.00")  # assumed fee per B/L corrected after the SI cut-off
ROLLOVER = Decimal("2000.00")  # assumed cost per booking rolled to the next vessel
Order = Literal["none", "fifo", "ranked"]


@dataclass(frozen=True)
class Outcome:
    bookings: int
    with_errors: int
    amendments: int
    rollovers: int
    not_catchable: int  # bookings whose only errors were consistent in every document

    @property
    def cost(self) -> Decimal:
        return self.amendments * AMENDMENT + self.rollovers * ROLLOVER


def day_of(m: Mismatch) -> int:
    return (m.cutoff - START).days


def replay(cs: list[Case], order: Order, per_day: int, rs: RuleSet | None = None) -> Outcome:
    """Each day the checker runs on what arrived; one analyst fixes `per_day` bookings with
    the shipper. A fix on day t clears the mismatches whose cut-off day is after t."""
    rs = rs or load()
    found = {c.shipment.booking.ref: run(c.shipment, rs) for c in cs}
    fixed: set[str] = set()
    if order != "none":
        last = max(c.received for c in cs) + 8
        for t in range(last):
            now = START + timedelta(days=t) - timedelta(hours=10)  # 08:00 on day t
            queue = [c for c in cs if c.received <= t and found[c.shipment.booking.ref]
                     and c.shipment.booking.ref not in fixed
                     and max(day_of(m) for m in found[c.shipment.booking.ref]) > t]
            if order == "fifo":
                queue.sort(key=lambda c: (c.received, c.shipment.booking.ref))
            else:
                first = {r.booking: i for i, r in reversed(list(enumerate(rank(
                    [m for c in queue for m in found[c.shipment.booking.ref]], now))))}
                queue.sort(key=lambda c: first[c.shipment.booking.ref])
            for c in queue[:per_day]:
                ref = c.shipment.booking.ref
                fixed.add(ref)
                found[ref] = [m for m in found[ref] if day_of(m) <= t]
    amend = roll = hidden = 0
    for c in cs:
        if not c.errors:
            continue
        ref = c.shipment.booking.ref
        left = c.errors if order == "none" or ref not in fixed else \
            tuple(e for e in c.errors if e == "truth" or any(
                (m.document == "vgm") == (e in VGM_ERRORS) for m in found[ref]))
        hidden += c.errors == ("truth",)
        amend += any(e not in VGM_ERRORS for e in left)
        roll += any(e in VGM_ERRORS for e in left)
    return Outcome(len(cs), sum(1 for c in cs if c.errors), amend, roll, hidden)


def compare(n: int = 600, seed: int = 11, rate: float = 0.03,
            per_day: int = 3) -> dict[Order, Outcome]:
    cs = cases(n, seed, rate)
    return {o: replay(cs, o, per_day) for o in ("none", "fifo", "ranked")}
