import random

import pytest

from bl_check.models import Shipment
from bl_check.synthetic import clean


@pytest.fixture
def ship() -> Shipment:
    s = clean(random.Random(1), 1, 0)
    # Hand-checkable: one 20 ft box, 20,000 kg cargo + 400 packing + 2,200 tare = 22,600.
    s.booking.size_type, s.booking.quantity, s.booking.packages = "22G1", 1, 500
    s.booking.hs_headings = ["3901"]
    num = s.vgm[0].container
    s.vgm = s.vgm[:1]
    v = s.vgm[0]
    v.cargo_kg, v.packing_kg, v.tare_kg, v.declared_kg = 20000, 400, 2200, 22600
    box = s.draft.containers[0]
    box.number, box.packages, box.gross_kg = num, 500, 20400
    s.draft.containers = [box]
    s.draft.hs_lines = s.draft.hs_lines[:1]
    h = s.draft.hs_lines[0]
    h.code, h.packages, h.gross_kg = "390110", 500, 20400
    return s
