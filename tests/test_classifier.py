"""Tests für classifier.classify_by_keyword (pure function, kein hass nötig)."""
from __future__ import annotations

from classifier import classify_by_keyword


CATS = ["Obst/Gemüse", "Gewürze", "Sonstiges"]


class TestLearnedCacheWins:
    def test_learned_takes_precedence(self):
        learned = {"paprika, edelsüß": "Gewürze"}
        keywords = {"paprika": "Obst/Gemüse"}
        assert (
            classify_by_keyword(
                "Paprika, edelsüß", keywords, learned, CATS
            )
            == "Gewürze"
        )

    def test_learned_skipped_if_category_no_longer_exists(self):
        learned = {"paprika": "RemovedCategory"}
        keywords = {"paprika": "Obst/Gemüse"}
        # Cache-Eintrag zeigt auf gelöschte Kategorie → fallback auf keyword
        assert (
            classify_by_keyword("paprika", keywords, learned, CATS)
            == "Obst/Gemüse"
        )


class TestCommaSkipsKeywords:
    def test_comma_in_item_skips_keyword_match(self):
        # 'paprika' als Keyword würde matchen, aber Komma → None → später LLM
        keywords = {"paprika": "Obst/Gemüse"}
        assert (
            classify_by_keyword(
                "Paprika, edelsüß", keywords, {}, CATS
            )
            is None
        )

    def test_no_comma_uses_keyword(self):
        keywords = {"paprika": "Obst/Gemüse"}
        assert (
            classify_by_keyword("Paprika", keywords, {}, CATS) == "Obst/Gemüse"
        )

    def test_comma_but_already_learned_returns_cache(self):
        learned = {"paprika, edelsüß": "Gewürze"}
        # Cache wird VOR der Komma-Regel gecheckt
        assert (
            classify_by_keyword(
                "Paprika, edelsüß", {}, learned, CATS
            )
            == "Gewürze"
        )


class TestLongestKeywordWins:
    def test_longer_keyword_overrides_shorter(self):
        keywords = {"ei": "Brot", "eier": "Brot/Eier"}
        cats = ["Brot", "Brot/Eier"]
        assert (
            classify_by_keyword("Eier", keywords, {}, cats) == "Brot/Eier"
        )


class TestUnknownItem:
    def test_returns_none_for_no_match(self):
        keywords = {"apfel": "Obst/Gemüse"}
        assert classify_by_keyword("Marzipan", keywords, {}, CATS) is None
