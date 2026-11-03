"""Rule engine. Rules live in JSON (which check, on which document, how severe, with
which tolerance); the checks themselves are small Python functions in `CHECKS`. A new rule
that reuses a check, or a change of tolerance, is a data change and needs no code."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from importlib import resources
from typing import Any, Literal

from .iso6346 import is_valid
from .models import Shipment

Document = Literal["vgm", "draft"]
Params = dict[str, Any]
Check = Callable[[Shipment, Params, dict[str, int]], list[str]]


def _norm(text: str) -> str:
    """Upper case, punctuation and repeated spaces removed: 'Acme Ltda.' == 'ACME  LTDA'."""
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", text.upper()).split())


def _off(a: int, b: int, pct: float) -> bool:
    return abs(a - b) > b * pct / 100


def check_digit(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    nums = [v.container for v in s.vgm] if p["source"] == "vgm" else \
        [c.number for c in s.draft.containers]
    return [f"{n} fails the ISO 6346 check digit" for n in nums if not is_valid(n)]


def same_containers(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    v, d = {x.container for x in s.vgm}, {c.number for c in s.draft.containers}
    out = [f"{n} has a VGM but is not on the draft" for n in sorted(v - d)]
    return out + [f"{n} is on the draft without a VGM" for n in sorted(d - v)]


def count_booked(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    n = len(s.draft.containers)
    return [] if n == s.booking.quantity else [f"draft has {n} containers, booked "
                                               f"{s.booking.quantity}"]


def vgm_sum(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    out = []
    for v in s.vgm:
        total = v.cargo_kg + v.packing_kg + v.tare_kg
        if _off(v.declared_kg, total, p["tolerance_pct"]):
            out.append(f"{v.container} declared {v.declared_kg} kg, cargo + packing + tare "
                       f"= {total} kg")
    return out


def max_gross(s: Shipment, p: Params, limits: dict[str, int]) -> list[str]:
    cap = limits[s.booking.size_type]
    return [f"{v.container} declared {v.declared_kg} kg, above {cap} kg for "
            f"{s.booking.size_type}" for v in s.vgm if v.declared_kg > cap]


def draft_weight(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    vgm = {v.container: v.cargo_kg + v.packing_kg for v in s.vgm}
    return [f"{c.number} draft {c.gross_kg} kg, VGM cargo + packing {vgm[c.number]} kg"
            for c in s.draft.containers
            if c.number in vgm and _off(c.gross_kg, vgm[c.number], p["tolerance_pct"])]


def same_consignee(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    a, b = _norm(s.booking.consignee), _norm(s.draft.consignee)
    return [] if a == b else [f"draft consignee '{s.draft.consignee}' is not the booked "
                              f"'{s.booking.consignee}'"]


def packages(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    boxes = sum(c.packages for c in s.draft.containers)
    lines = sum(h.packages for h in s.draft.hs_lines)
    out = [] if boxes == s.booking.packages else [f"draft containers hold {boxes} packages, "
                                                  f"booked {s.booking.packages}"]
    return out + ([] if lines == boxes else [f"HS lines sum to {lines} packages, containers "
                                             f"to {boxes}"])


def hs_lines(s: Shipment, p: Params, _: dict[str, int]) -> list[str]:
    out = []
    for h in s.draft.hs_lines:
        if not re.fullmatch(r"\d{6,10}", h.code):
            out.append(f"HS code {h.code} is not 6 to 10 digits")
        elif h.code[:4] not in s.booking.hs_headings:
            out.append(f"HS code {h.code} is outside the booked headings")
    kg = sum(h.gross_kg for h in s.draft.hs_lines)
    boxes = sum(c.gross_kg for c in s.draft.containers)
    return out + ([] if kg == boxes else [f"HS lines sum to {kg} kg, containers to {boxes}"])


CHECKS: dict[str, Check] = {f.__name__: f for f in (
    check_digit, same_containers, count_booked, vgm_sum, max_gross, draft_weight,
    same_consignee, packages, hs_lines)}


@dataclass(frozen=True)
class Rule:
    id: str
    check: str
    document: Document
    severity: int
    params: Params


@dataclass(frozen=True)
class RuleSet:
    rules: tuple[Rule, ...]
    max_gross_kg: dict[str, int]


def load(text: str | None = None) -> RuleSet:
    """Parse a rule file; default is the bundled rules.json. Unknown checks are refused."""
    raw = json.loads(text if text is not None else
                     resources.files("bl_check").joinpath("rules.json").read_text())
    rules = tuple(Rule(**r) for r in raw["rules"])
    for r in rules:
        if r.check not in CHECKS:
            raise ValueError(f"rule {r.id}: unknown check '{r.check}'")
        if r.document not in ("vgm", "draft"):
            raise ValueError(f"rule {r.id}: document must be vgm or draft")
    return RuleSet(rules, raw["max_gross_kg"])


@dataclass(frozen=True)
class Mismatch:
    booking: str
    rule: str
    document: Document
    severity: int
    detail: str
    cutoff: datetime

    def hours_left(self, now: datetime) -> float:
        return (self.cutoff - now).total_seconds() / 3600


def run(s: Shipment, rs: RuleSet) -> list[Mismatch]:
    b = s.booking
    return [Mismatch(b.ref, r.id, r.document, r.severity, d,
                     b.vgm_cutoff if r.document == "vgm" else b.si_cutoff)
            for r in rs.rules for d in CHECKS[r.check](s, r.params, rs.max_gross_kg)]


def rank(found: list[Mismatch], now: datetime) -> list[Mismatch]:
    """Nearest cut-off first, then the most severe. Missed cut-offs go to the end."""
    return sorted(found, key=lambda m: (m.cutoff < now, m.cutoff, -m.severity, m.booking,
                                        m.rule))
