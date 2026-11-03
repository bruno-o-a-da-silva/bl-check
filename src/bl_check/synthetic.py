"""Seeded synthetic bookings with errors injected at a stated rate per error type."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from .iso6346 import check_digit
from .models import Booking, Draft, DraftContainer, HsLine, Shipment, Vgm

START = datetime(2026, 3, 2, 18, 0)  # cut-offs fall at 18:00
HEADINGS = ("3901", "3902", "3907", "2902", "3824")
TARE = {"22G1": 2200, "45G1": 3900}
NAMES = ("Atlas Quimica Ltda", "Porto Verde Polimeros SA", "Nordeste Resinas Ltda",
         "Delta Plast Comercio Ltda", "Rio Claro Solventes SA", "Vale Sul Embalagens Ltda")
# Errors a person makes typing one document; "truth" is wrong in every document alike.
ERRORS = ("box_digit", "vgm_math", "draft_weight", "consignee", "packages", "hs", "truth")
VGM_ERRORS = frozenset({"vgm_math"})


@dataclass(frozen=True)
class Case:
    shipment: Shipment
    received: int  # day the VGM and draft arrive
    errors: tuple[str, ...]


def container(rng: random.Random) -> str:
    head = "QXTU" + f"{rng.randint(0, 999_999):06d}"
    return head + str(check_digit(head))


def clean(rng: random.Random, n: int, received: int) -> Shipment:
    size = rng.choice(("22G1", "45G1"))
    heads = sorted(rng.sample(HEADINGS, rng.randint(1, 2)))
    si = START + timedelta(days=received + rng.randint(2, 6))
    vgms, boxes = [], []
    for _ in range(rng.randint(1, 4)):
        num, cargo, packing = container(rng), rng.randint(8000, 24000), rng.randint(200, 600)
        vgms.append(Vgm(container=num, cargo_kg=cargo, packing_kg=packing, tare_kg=TARE[size],
                        declared_kg=cargo + packing + TARE[size]))
        boxes.append(DraftContainer(number=num, packages=rng.randint(100, 900),
                                    gross_kg=cargo + packing))
    pk, kg = sum(b.packages for b in boxes), sum(b.gross_kg for b in boxes)
    lines = [HsLine(code=h + "10", packages=pk // len(heads), gross_kg=kg // len(heads))
             for h in heads]
    lines[0] = HsLine(code=lines[0].code, packages=pk - sum(x.packages for x in lines[1:]),
                      gross_kg=kg - sum(x.gross_kg for x in lines[1:]))
    name = rng.choice(NAMES)
    return Shipment(
        booking=Booking(ref=f"BK{n:05d}", consignee=name, quantity=len(boxes), size_type=size,
                        packages=pk, hs_headings=heads, si_cutoff=si,
                        vgm_cutoff=si + timedelta(days=1)),
        vgm=vgms, draft=Draft(consignee=name.upper(), containers=boxes, hs_lines=lines))


def inject(rng: random.Random, s: Shipment, kind: str) -> Shipment:
    s = s.model_copy(deep=True)
    box = s.draft.containers[0]
    if kind == "box_digit":
        box.number = box.number[:10] + str((int(box.number[10]) + rng.randint(1, 9)) % 10)
    elif kind == "vgm_math":
        v = s.vgm[0]
        v.declared_kg = round(v.declared_kg * rng.uniform(1.08, 1.15))
    elif kind == "draft_weight":
        box.gross_kg = round(box.gross_kg * rng.uniform(1.1, 1.5))
    elif kind == "consignee":
        s.draft.consignee = rng.choice([n for n in NAMES if n.upper() != s.draft.consignee])
    elif kind == "packages":
        box.packages += rng.randint(5, 50)
    elif kind == "hs":
        line = s.draft.hs_lines[0]
        line.code = rng.choice([h for h in HEADINGS if h not in s.booking.hs_headings]) + "10"
    else:  # truth: the shipper booked the wrong consignee and copied it everywhere
        wrong = rng.choice([n for n in NAMES if n != s.booking.consignee])
        s.booking.consignee, s.draft.consignee = wrong, wrong
    return s


def cases(n: int, seed: int, rate: float, days: int = 25) -> list[Case]:
    """`rate` is the chance, per booking and per error type, that the error is injected."""
    rng = random.Random(seed)
    out = []
    for k in range(n):
        received = rng.randint(0, days - 1)
        s = clean(rng, k + 1, received)
        errs = tuple(e for e in ERRORS if rng.random() < rate)
        for e in errs:
            s = inject(rng, s, e)
        out.append(Case(s, received, errs))
    return out
