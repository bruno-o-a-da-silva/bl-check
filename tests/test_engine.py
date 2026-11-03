import random
from datetime import datetime, timedelta

import pytest

from bl_check.engine import _norm, load, rank, run
from bl_check.models import Shipment
from bl_check.synthetic import ERRORS, inject

RS = load()


def ids(s: Shipment) -> set[str]:
    return {m.rule for m in run(s, RS)}


def test_clean_shipment_passes(ship: Shipment) -> None:
    assert run(ship, RS) == []


def test_vgm_tolerance_hand_case(ship: Shipment) -> None:
    ship.vgm[0].declared_kg = 22600 + 1130  # exactly 5% over: accepted
    assert ids(ship) == set()
    ship.vgm[0].declared_kg = 22600 + 1131
    assert ids(ship) == {"VGM-SUM"}
    ship.vgm[0].cargo_kg = 30000
    ship.vgm[0].declared_kg = 32600
    assert "VGM-MAX" in ids(ship)  # above 30,480 kg for a 22G1


@pytest.mark.parametrize(("kind", "expected"), [
    ("box_digit", {"BL-DIGIT", "BOX-SET"}),
    ("vgm_math", {"VGM-SUM"}),
    ("draft_weight", {"BL-WEIGHT", "HS-LINES"}),
    ("consignee", {"CONSIGNEE"}),
    ("packages", {"PACKAGES"}),
    ("hs", {"HS-LINES"}),
    ("truth", set()),  # wrong in every document alike: rules cannot see it
])
def test_each_injected_error(ship: Shipment, kind: str, expected: set[str]) -> None:
    assert kind in ERRORS
    assert ids(inject(random.Random(2), ship, kind)) == expected


def test_other_rules(ship: Shipment) -> None:
    ship.booking.quantity = 2
    ship.draft.hs_lines[0].code = "3901"
    ship.vgm[0].container = "CSQU3054384"
    assert ids(ship) == {"BOX-COUNT", "HS-LINES", "VGM-DIGIT", "BOX-SET"}
    assert _norm(" Atlas  Quimica Ltda. ") == "ATLAS QUIMICA LTDA"


def test_rule_file_is_validated() -> None:
    with pytest.raises(ValueError, match="unknown check"):
        load('{"max_gross_kg": {}, "rules": [{"id": "X", "check": "nope", "document": '
             '"vgm", "severity": 1, "params": {}}]}')
    with pytest.raises(ValueError, match="document"):
        load('{"max_gross_kg": {}, "rules": [{"id": "X", "check": "packages", "document": '
             '"invoice", "severity": 1, "params": {}}]}')


def test_ranking_by_cutoff_then_severity(ship: Shipment) -> None:
    ship.vgm[0].declared_kg = 30000          # VGM-SUM, severity 3, VGM cut-off (later)
    ship.draft.containers[0].packages = 510  # PACKAGES, severity 1, SI cut-off
    ship.draft.consignee = "Someone Else"    # CONSIGNEE, severity 2, SI cut-off
    si = ship.booking.si_cutoff
    order = [m.rule for m in rank(run(ship, RS), si - timedelta(hours=5))]
    assert order == ["CONSIGNEE", "PACKAGES", "PACKAGES", "VGM-SUM"]
    late = rank(run(ship, RS), si + timedelta(hours=1))
    assert late[0].rule == "VGM-SUM"         # missed cut-offs go last
    assert late[0].hours_left(si + timedelta(hours=1)) == 23.0
    assert isinstance(si, datetime)
