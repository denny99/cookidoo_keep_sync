"""Tests für quantities.py — Parser + Aggregator."""
from __future__ import annotations

import pytest

from quantities import (
    Quantity,
    aggregate,
    normalize_for_dedup,
    parse_qty,
    split_name_qty,
)


class TestParseQty:
    @pytest.mark.parametrize(
        "text,expected_amount,expected_unit",
        [
            ("70 g", 70.0, "g"),
            ("70g", 70.0, "g"),
            ("0,5 kg", 0.5, "kg"),
            ("0.5 kg", 0.5, "kg"),
            ("1/2 TL", 0.5, "tl"),
            ("3/4 EL", 0.75, "el"),
            ("1 Stk", 1.0, "stk"),
            ("1 Stk.", 1.0, "stk"),
            ("2 Zehen", 2.0, "zehen"),
            ("1 Prise", 1.0, "prise"),
            ("100", 100.0, ""),
            ("1-2 EL", 2.0, "el"),  # Range nimmt obere Grenze
            ("1,5-2 kg", 2.0, "kg"),
        ],
    )
    def test_parses(self, text: str, expected_amount: float, expected_unit: str):
        result = parse_qty(text)
        assert result is not None
        assert result.amount == pytest.approx(expected_amount)
        assert result.unit == expected_unit

    @pytest.mark.parametrize("text", ["", "  ", None, "abc", "etwas"])
    def test_unparseable(self, text: str | None):
        assert parse_qty(text) is None  # type: ignore[arg-type]


class TestAggregateSameUnit:
    def test_grams_summed(self):
        assert aggregate(["70 g", "50 g"]) == "120 g"

    def test_pieces_summed(self):
        assert aggregate(["1 Stk", "2 Stk"]) == "3 Stk"

    def test_dot_unit_normalized(self):
        assert aggregate(["1 Stk.", "2 Stk"]) == "3 Stk"

    def test_plurals_merged(self):
        assert aggregate(["1 Zehe", "2 Zehen"]) == "3 Zehe"

    def test_prise(self):
        assert aggregate(["1 Prise", "1 Prise"]) == "2 Prise"


class TestAggregateConversion:
    def test_g_to_kg_when_over_1000(self):
        assert aggregate(["800 g", "0,5 kg"]) == "1,3 kg"

    def test_under_1000g_stays_g(self):
        assert aggregate(["100 g", "200 g"]) == "300 g"

    def test_ml_to_l(self):
        assert aggregate(["500 ml", "1 l"]) == "1,5 l"

    def test_volume_under_1l(self):
        assert aggregate(["0,5 l", "200 ml"]) == "700 ml"

    def test_el_tl_normalized(self):
        # 2 EL + 1 EL = 3 EL
        assert aggregate(["2 EL", "1 EL"]) == "3 EL"

    def test_el_tl_mixed_displays_in_el_when_over_one(self):
        # 1 EL = 3 TL; 1 EL + 2 TL = 5 TL = 1.67 EL
        assert aggregate(["1 EL", "2 TL"]) == "1,67 EL"

    def test_el_tl_under_one_el_displays_in_tl(self):
        # 0.5 TL + 0.25 TL = 0.75 TL — bleibt in TL
        assert aggregate(["1/2 TL", "1/4 TL"]) == "0,75 TL"


class TestAggregateMixedGroups:
    def test_mass_plus_count(self):
        assert aggregate(["70 g", "1 Stk"]) == "70 g + 1 Stk"

    def test_keeps_unparseable_separate(self):
        result = aggregate(["nach Geschmack", "1 Prise"])
        assert "1 Prise" in result
        assert "nach Geschmack" in result

    def test_dedupes_unparseable(self):
        assert aggregate(["nach Geschmack", "nach Geschmack"]) == "nach Geschmack"

    def test_three_groups(self):
        result = aggregate(["100 g", "1 EL", "2 Stk"])
        assert "100 g" in result
        assert "1 EL" in result
        assert "2 Stk" in result


class TestAggregateEdgeCases:
    def test_empty_list(self):
        assert aggregate([]) == ""

    def test_only_blanks(self):
        assert aggregate(["", "  ", None]) == ""  # type: ignore[list-item]

    def test_single_item(self):
        assert aggregate(["100 g"]) == "100 g"


class TestSplitNameQty:
    @pytest.mark.parametrize(
        "summary,expected_name,expected_qty",
        [
            ("Zwiebeln 70 g", "Zwiebeln", "70 g"),
            ("Tomaten, 200g", "Tomaten", "200g"),
            ("Knoblauch 2 Zehen", "Knoblauch", "2 Zehen"),
            ("Olivenöl 1 EL", "Olivenöl", "1 EL"),
            ("Eier 6 Stk", "Eier", "6 Stk"),
            # Keine erkennbare Einheit → nicht splitten
            ("Mehl Type 405", "Mehl Type 405", ""),
            ("Salz", "Salz", ""),
            ("Tomaten", "Tomaten", ""),
            # Schon enthaltene Klammer wird nicht gesplittet
            ("Mehl (Vollkorn)", "Mehl (Vollkorn)", ""),
        ],
    )
    def test_split(self, summary: str, expected_name: str, expected_qty: str):
        name, qty = split_name_qty(summary)
        assert name == expected_name
        assert qty == expected_qty


class TestNormalizeForDedup:
    @pytest.mark.parametrize(
        "summary,expected",
        [
            ("Zwiebeln (70 g)", "zwiebeln"),
            ("zwiebeln", "zwiebeln"),
            ("Zwiebeln", "zwiebeln"),
            ("Tomaten (Bio)", "tomaten"),
            ("  Mehl  ", "mehl"),
            ("Mehl (Type 405)", "mehl"),
            # Klammer mitten im Text bleibt — wir entfernen nur trailing
            ("Mehl (Type 405) extra", "mehl (type 405) extra"),
        ],
    )
    def test_normalize(self, summary: str, expected: str):
        assert normalize_for_dedup(summary) == expected


class TestRealisticScenarios:
    """Realistische Cookidoo-Szenarien aus mehreren Rezepten."""

    def test_zwiebeln_two_recipes(self):
        # Rezept 1: 70 g Zwiebeln, Rezept 2: 1 Stk Zwiebel
        # → unterschiedliche Einheiten, beide angezeigt
        assert aggregate(["70 g", "1 Stk"]) == "70 g + 1 Stk"

    def test_butter_g_and_el(self):
        # Rezept 1: 50 g Butter, Rezept 2: 1 EL Butter
        result = aggregate(["50 g", "1 EL"])
        assert "50 g" in result
        assert "1 EL" in result

    def test_kraeuter_prise_and_tl(self):
        result = aggregate(["1 Prise", "1/2 TL"])
        assert "1 Prise" in result
        assert "0,5 TL" in result

    def test_mehl_aufgesummt(self):
        # 250 g + 250 g + 500 g = 1 kg
        assert aggregate(["250 g", "250 g", "500 g"]) == "1 kg"
