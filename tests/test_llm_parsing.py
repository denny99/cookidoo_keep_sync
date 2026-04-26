"""Tests für die LLM-Output-Parser — die wahrscheinlichste Bug-Quelle, weil
verschiedene Conversation-Agents (Claude, OpenAI, Ollama, ...) ihre Antworten
unterschiedlich formatieren."""
from __future__ import annotations

import pytest

from classifier import extract_speech, parse_bulk_response


CATS = ["Obst/Gemüse", "Gewürze", "Fleisch", "Sonstiges"]


class TestParseBulkResponseHappyPath:
    def test_perfect_format(self):
        text = "[1] Obst/Gemüse\n[2] Fleisch"
        items = ["Tomaten", "Hähnchen"]
        assert parse_bulk_response(text, items, CATS) == {
            "Tomaten": "Obst/Gemüse",
            "Hähnchen": "Fleisch",
        }

    def test_extra_whitespace_around(self):
        text = "  [1]  Obst/Gemüse  \n\n  [2]   Fleisch\n"
        items = ["Tomaten", "Hähnchen"]
        assert parse_bulk_response(text, items, CATS) == {
            "Tomaten": "Obst/Gemüse",
            "Hähnchen": "Fleisch",
        }

    def test_trailing_punctuation_stripped(self):
        text = "[1] Obst/Gemüse.\n[2] \"Fleisch\""
        items = ["Tomaten", "Hähnchen"]
        assert parse_bulk_response(text, items, CATS) == {
            "Tomaten": "Obst/Gemüse",
            "Hähnchen": "Fleisch",
        }


class TestParseBulkResponseFuzzy:
    def test_case_insensitive_category_match(self):
        text = "[1] obst/gemüse"
        assert parse_bulk_response(text, ["Tomaten"], CATS) == {
            "Tomaten": "Obst/Gemüse",
        }

    def test_substring_match_fallback(self):
        # LLM antwortet mit "Gemüse" — nicht exakt aber substring-match auf "Obst/Gemüse"
        text = "[1] Gemüse"
        assert parse_bulk_response(text, ["Tomaten"], CATS) == {
            "Tomaten": "Obst/Gemüse",
        }


class TestParseBulkResponseRobustness:
    def test_unknown_line_ignored(self):
        text = "Hier sind die Klassifikationen:\n[1] Obst/Gemüse\nWeitere Frage?"
        assert parse_bulk_response(text, ["Tomaten"], CATS) == {
            "Tomaten": "Obst/Gemüse",
        }

    def test_unmatched_category_skipped(self):
        # LLM erfindet eine Kategorie, die nicht existiert
        text = "[1] Halluziniert"
        assert parse_bulk_response(text, ["Tomaten"], CATS) == {}

    def test_out_of_range_index_ignored(self):
        text = "[5] Obst/Gemüse"
        assert parse_bulk_response(text, ["Tomaten"], CATS) == {}

    def test_zero_index_ignored(self):
        text = "[0] Obst/Gemüse"
        assert parse_bulk_response(text, ["Tomaten"], CATS) == {}

    def test_empty_response(self):
        assert parse_bulk_response("", ["Tomaten"], CATS) == {}

    def test_partial_response(self):
        # LLM klassifiziert nur 2 von 3 Items
        text = "[1] Obst/Gemüse\n[3] Fleisch"
        items = ["Tomaten", "Brot", "Hähnchen"]
        assert parse_bulk_response(text, items, CATS) == {
            "Tomaten": "Obst/Gemüse",
            "Hähnchen": "Fleisch",
        }


class TestExtractSpeech:
    def test_normal_response(self):
        response = {
            "response": {"speech": {"plain": {"speech": "Hello world"}}}
        }
        assert extract_speech(response) == "Hello world"

    def test_empty_response(self):
        assert extract_speech(None) is None
        assert extract_speech({}) is None

    def test_malformed_response(self):
        # Verschiedene Stellen wo der erwartete Pfad fehlt
        assert extract_speech({"response": None}) is None
        assert extract_speech({"response": {"speech": {}}}) is None
        assert extract_speech({"response": {"speech": {"plain": {}}}}) is None
        assert extract_speech({"foo": "bar"}) is None
