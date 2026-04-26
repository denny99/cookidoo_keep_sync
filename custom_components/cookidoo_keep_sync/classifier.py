"""Klassifiziert Items in Kategorien per Keyword-Match + LLM-Fallback."""
from __future__ import annotations

import logging
import re

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

UNKNOWN = "Sonstiges"

# Erwartetes Antwort-Format pro Zeile: [NUMMER] Kategoriename
_BULK_LINE_RE = re.compile(r"^\s*\[(\d+)\]\s*(.+?)\s*$")


def classify_by_keyword(
    item: str,
    keywords: dict[str, str],
    learned: dict[str, str],
    categories: list[str],
) -> str | None:
    """Match item against learned + keyword dict. Returns category or None."""
    norm = item.lower().strip()

    if norm in learned and learned[norm] in categories:
        return learned[norm]

    # Längstes Keyword zuerst, damit "eier" vor "ei" matcht
    for kw in sorted(keywords.keys(), key=len, reverse=True):
        if kw in norm and keywords[kw] in categories:
            return keywords[kw]

    return None


async def classify_bulk_with_llm(
    hass: HomeAssistant,
    items: list[str],
    categories: list[str],
    agent_id: str,
) -> dict[str, str]:
    """Klassifiziert alle Items in EINEM LLM-Call.

    Antwortformat pro Zeile: '[N] Kategoriename'.
    Items, die der Agent nicht zuordnet, fehlen im Result-Dict.
    """
    if not items:
        return {}

    cat_list = "\n".join(f"- {c}" for c in categories)
    numbered = "\n".join(f"{i + 1}. {it}" for i, it in enumerate(items))
    prompt = (
        "Du sortierst Einkaufsartikel in Supermarkt-Kategorien.\n"
        "Erlaubte Kategorien (verwende nur diese exakten Namen):\n"
        f"{cat_list}\n\n"
        "Artikel:\n"
        f"{numbered}\n\n"
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
        _LOGGER.debug("Bulk-LLM hat %d/%d Items nicht klassifiziert: %s",
                      len(missing), len(items), missing)

    return result


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
