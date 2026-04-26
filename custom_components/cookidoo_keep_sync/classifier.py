"""Klassifiziert Items per Lerncache (Phase 1) + LLM-Bulk-Call (Phase 2).

Es gibt bewusst keinen Keyword-/Substring-Matcher mehr: der Cache klassifiziert
identische Item-Namen sofort, neue Items gehen ans LLM. Cookidoo wiederholt
Zutatennamen über Rezepte hinweg, also stabilisiert sich das schnell.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

UNKNOWN = "Sonstiges"

# Erwartetes Antwort-Format pro Zeile: [NUMMER] Kategoriename
_BULK_LINE_RE = re.compile(r"^\s*\[(\d+)\]\s*(.+?)\s*$")


def classify_from_cache(
    item: str,
    learned: dict[str, str],
    categories: list[str],
) -> str | None:
    """Sucht das Item im Lerncache. Stale Einträge (Kategorie existiert nicht
    mehr in `categories`) werden ignoriert."""
    norm = item.lower().strip()
    if norm in learned and learned[norm] in categories:
        return learned[norm]
    return None


async def classify_bulk_with_llm(
    hass: "HomeAssistant",
    items: list[str],
    categories: list[str],
    agent_id: str,
    learned: dict[str, str] | None = None,
) -> dict[str, str]:
    """Klassifiziert alle Items in EINEM LLM-Call. Wenn `learned` mitgegeben
    wird, werden bis zu 2 Beispiele pro Kategorie als Calibration in den
    Prompt eingebettet, damit der LLM die persönlichen Schemata des Users
    übernimmt und nicht dauernd die gleichen Fehler macht."""
    if not items:
        return {}

    cat_list = "\n".join(f"- {c}" for c in categories)
    numbered = "\n".join(f"{i + 1}. {it}" for i, it in enumerate(items))

    examples_block = ""
    if learned:
        examples = select_examples(learned, categories, max_per_category=2)
        if examples:
            lines = "\n".join(f"- {item} → {cat}" for item, cat in examples)
            examples_block = (
                "\nBekannte Beispiele aus früheren Klassifikationen "
                "(folge diesem Schema, auch bei Grenzfällen):\n"
                f"{lines}\n"
            )

    prompt = (
        "Du sortierst Einkaufsartikel in Supermarkt-Kategorien.\n"
        f"Erlaubte Kategorien (verwende nur diese exakten Namen):\n{cat_list}\n"
        f"{examples_block}"
        f"\nNeue Artikel:\n{numbered}\n\n"
        "Antworte für JEDEN Artikel mit GENAU einer Zeile im Format:\n"
        "[NUMMER] Kategoriename\n"
        "Keine Erklärungen, kein Markdown, keine Leerzeilen, keine zusätzlichen Zeichen.\n"
        f"Beispiel: [1] {categories[0]}"
    )

    try:
        response = await hass.services.async_call(
            "conversation",
            "process",
            {"agent_id": agent_id, "text": prompt},
            blocking=True,
            return_response=True,
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Bulk-LLM-Klassifikation fehlgeschlagen: %s", err)
        return {}

    text = _extract_speech(response) or ""
    cat_lower = {c.lower(): c for c in categories}
    result: dict[str, str] = {}

    for line in text.splitlines():
        match = _BULK_LINE_RE.match(line)
        if not match:
            continue
        try:
            num = int(match.group(1))
        except ValueError:
            continue
        if not 1 <= num <= len(items):
            continue
        raw_cat = match.group(2).strip().strip(".'\"")
        cat = _resolve_category(raw_cat, cat_lower)
        if cat:
            result[items[num - 1]] = cat

    if len(result) < len(items):
        missing = [it for it in items if it not in result]
        _LOGGER.debug(
            "Bulk-LLM hat %d/%d Items nicht klassifiziert: %s",
            len(missing), len(items), missing,
        )

    return result


def select_examples(
    learned: dict[str, str],
    categories: list[str],
    max_per_category: int = 2,
) -> list[tuple[str, str]]:
    """Wählt bis zu `max_per_category` Beispiel-Mappings pro Kategorie aus dem
    Lerncache. Reihenfolge: Kategorien wie übergeben (also wie in der
    Markt-Sortierung), innerhalb alphabetisch nach Item-Name."""
    by_cat: dict[str, list[str]] = {}
    for item, cat in learned.items():
        if cat in categories:
            by_cat.setdefault(cat, []).append(item)
    out: list[tuple[str, str]] = []
    for cat in categories:
        items = sorted(by_cat.get(cat, []))[:max_per_category]
        for item in items:
            out.append((item, cat))
    return out


def _resolve_category(raw: str, cat_lower: dict[str, str]) -> str | None:
    low = raw.lower()
    if low in cat_lower:
        return cat_lower[low]
    for cat_l, cat in cat_lower.items():
        if cat_l in low or low in cat_l:
            return cat
    return None


def _extract_speech(response: dict | None) -> str | None:
    if not response:
        return None
    try:
        return response["response"]["speech"]["plain"]["speech"]
    except (KeyError, TypeError):
        return None
