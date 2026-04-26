"""Tests für strip_qty_parens — entfernt nur trailing '(...)' Quantity-Hänger."""
from __future__ import annotations

import pytest

from quantities import strip_qty_parens


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Zwiebeln (70 g)", "Zwiebeln"),
        ("Zwiebeln", "Zwiebeln"),
        ("Paprika, edelsüß (1 TL)", "Paprika, edelsüß"),
        ("Mehl (Type 405)", "Mehl"),
        # Klammer mitten im Text bleibt unverändert
        ("Mehl (Vollkorn) extra", "Mehl (Vollkorn) extra"),
        ("  Brot (1 Stk)  ", "Brot"),
    ],
)
def test_strip(raw: str, expected: str):
    assert strip_qty_parens(raw) == expected
