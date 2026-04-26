"""Tests für die pure Klassifikator-Funktionen (kein hass nötig)."""
from __future__ import annotations

from classifier import classify_from_cache, select_examples


CATS = ["Obst/Gemüse", "Gewürze", "Sonstiges"]


class TestClassifyFromCache:
    def test_hit(self):
        learned = {"paprika, edelsüß": "Gewürze"}
        assert (
            classify_from_cache("Paprika, edelsüß", learned, CATS) == "Gewürze"
        )

    def test_case_insensitive_lookup(self):
        learned = {"tomaten": "Obst/Gemüse"}
        assert classify_from_cache("Tomaten", learned, CATS) == "Obst/Gemüse"
        assert classify_from_cache("TOMATEN", learned, CATS) == "Obst/Gemüse"

    def test_miss_returns_none(self):
        assert classify_from_cache("Marzipan", {}, CATS) is None

    def test_stale_category_ignored(self):
        learned = {"paprika": "RemovedCategory"}
        # Cache zeigt auf nicht mehr existierende Kategorie → Miss
        assert classify_from_cache("Paprika", learned, CATS) is None


class TestSelectExamples:
    def test_picks_one_per_category_alphabetically(self):
        learned = {
            "tomaten": "Obst/Gemüse",
            "apfel": "Obst/Gemüse",
            "banane": "Obst/Gemüse",
            "pfeffer": "Gewürze",
        }
        ex = select_examples(learned, CATS, max_per_category=2)
        # Reihenfolge: Kategorien wie übergeben (Obst zuerst), dann alphabetisch
        assert ex == [
            ("apfel", "Obst/Gemüse"),
            ("banane", "Obst/Gemüse"),
            ("pfeffer", "Gewürze"),
        ]

    def test_skips_stale_categories(self):
        learned = {"foo": "RemovedCategory", "tomaten": "Obst/Gemüse"}
        ex = select_examples(learned, CATS)
        assert ex == [("tomaten", "Obst/Gemüse")]

    def test_empty_input(self):
        assert select_examples({}, CATS) == []
        assert select_examples({"foo": "Bar"}, []) == []

    def test_respects_max_per_category(self):
        learned = {f"item{i}": "Obst/Gemüse" for i in range(10)}
        ex = select_examples(learned, CATS, max_per_category=3)
        assert len(ex) == 3
