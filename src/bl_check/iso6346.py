"""ISO 6346 container number: owner code, category (U, J or Z), six digits, check digit."""

from __future__ import annotations

import re

PATTERN = re.compile(r"^[A-Z]{3}[UJZ]\d{7}$")


def _letter_values() -> dict[str, int]:
    """A = 10, counting up but skipping multiples of 11 (11, 22, 33)."""
    out, v = {}, 10
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if v % 11 == 0:
            v += 1
        out[ch] = v
        v += 1
    return out


VALUES = _letter_values()


def check_digit(first10: str) -> int:
    """Sum of value x 2^position over the first ten characters, mod 11, then mod 10."""
    total = sum((VALUES[c] if c.isalpha() else int(c)) * (1 << i) for i, c in enumerate(first10))
    return total % 11 % 10


def is_valid(number: str) -> bool:
    n = number.replace(" ", "").upper()
    return bool(PATTERN.match(n)) and check_digit(n[:10]) == int(n[10])
