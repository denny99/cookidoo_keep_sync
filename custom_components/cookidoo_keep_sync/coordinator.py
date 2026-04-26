"""Sync-Logik: Cookidoo lesen → mit Keep mergen → klassifizieren → sortiert schreiben."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .classifier import UNKNOWN, classify_bulk_with_llm, classify_by_keyword
from .const import (
    CONF_CATEGORIES,
    CONF_CATEGORIES_ENTITY,
    CONF_CONVERSATION_AGENT,
    CONF_COOKIDOO_ENTITY,
    CONF_KEEP_ENTITY,
    CONF_KEYWORDS,
    CONF_USE_LLM,
    DEFAULT_CATEGORIES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1

# Im todo-Component-Standard: Status NEEDS_ACTION = offen, COMPLETED = abgehakt
STATUS_OPEN = "needs_action"


def storage_key(entry_id: str) -> str:
    return f"{DOMAIN}_{entry_id}_learned"


async def async_load_learned(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    store: Store = Store(hass, STORAGE_VERSION, storage_key(entry_id))
    data = await store.async_load()
    return data or {}


async def async_save_learned(
    hass: HomeAssistant, entry_id: str, learned: dict[str, str]
) -> None:
    store: Store = Store(hass, STORAGE_VERSION, storage_key(entry_id))
    await store.async_save(learned)


async def async_get_todo_items(
    hass: HomeAssistant, entity_id: str
) -> list[dict]:
    response = await hass.services.async_call(
        "todo",
        "get_items",
        {"entity_id": entity_id},
        blocking=True,
        return_response=True,
    )
    if not response:
        return []
    bucket = response.get(entity_id) or {}
    return bucket.get("items", [])


async def async_remove_item(
    hass: HomeAssistant, entity_id: str, summary: str
) -> None:
    await hass.services.async_call(
        "todo",
        "remove_item",
        {"entity_id": entity_id, "item": summary},
        blocking=True,
    )


async def async_add_item(
    hass: HomeAssistant, entity_id: str, summary: str
) -> None:
    await hass.services.async_call(
        "todo",
        "add_item",
        {"entity_id": entity_id, "item": summary},
        blocking=True,
    )


async def async_complete_item(
    hass: HomeAssistant, entity_id: str, summary: str
) -> None:
    """Markiert ein Item als erledigt. Manche Integrationen verweigern das (read-only) –
    Fehler werden geloggt, aber nicht propagiert."""
    try:
        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": entity_id,
                "item": summary,
                "status": "completed",
            },
            blocking=True,
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug(
            "Konnte '%s' in %s nicht abhaken (read-only?): %s",
            summary, entity_id, err,
        )


async def _resolve_categories(
    hass: HomeAssistant, entry_id: str, options: dict
) -> list[str]:
    """Quelle der Kategorien-Reihenfolge: konfigurierter Override, sonst eigene
    Entity der Integration, sonst Defaults."""
    override = options.get(CONF_CATEGORIES_ENTITY)
    if override:
        items = await async_get_todo_items(hass, override)
        cats = [(it.get("summary") or "").strip() for it in items]
        cats = [c for c in cats if c]
        if cats:
            return cats
    own = hass.data[DOMAIN][entry_id].get("categories_entity")
    if own:
        cats = own.category_names()
        if cats:
            return cats
    return options.get(CONF_CATEGORIES) or DEFAULT_CATEGORIES


def _is_open(item: dict) -> bool:
    status = (item.get("status") or "").lower()
    # Manche Integrationen liefern keinen status → als offen behandeln
    return status in ("", STATUS_OPEN)


async def async_run_sync(hass: HomeAssistant, entry_id: str) -> dict:
    """Mergt Cookidoo + offene Keep-Items, klassifiziert, schreibt sortiert."""
    data = hass.data[DOMAIN][entry_id]
    options = data["options"]

    cookidoo_entity: str = options[CONF_COOKIDOO_ENTITY]
    keep_entity: str = options[CONF_KEEP_ENTITY]
    agent_id: str | None = options.get(CONF_CONVERSATION_AGENT)
    categories = await _resolve_categories(hass, entry_id, options)
    keywords: dict[str, str] = options.get(CONF_KEYWORDS) or {}
    use_llm: bool = options.get(CONF_USE_LLM, True) and bool(agent_id)

    learned: dict[str, str] = await async_load_learned(hass, entry_id)

    cookidoo_items = await async_get_todo_items(hass, cookidoo_entity)
    keep_items = await async_get_todo_items(hass, keep_entity)

    # Offene Items aus beiden Quellen sammeln, Reihenfolge erhalten, dedupen.
    # cookidoo_originals merken, um sie nach erfolgreichem Kopieren abzuhaken.
    seen: set[str] = set()
    combined: list[str] = []
    cookidoo_originals: dict[str, str] = {}  # lower -> original-summary in Cookidoo

    def _push(summary: str) -> None:
        s = summary.strip()
        if not s:
            return
        key = s.lower()
        if key in seen:
            return
        seen.add(key)
        combined.append(s)

    for it in cookidoo_items:
        if not _is_open(it):
            continue
        summary = (it.get("summary") or "").strip()
        if summary:
            cookidoo_originals[summary.lower()] = summary
            _push(summary)
    for it in keep_items:
        if _is_open(it):
            _push(it.get("summary") or "")

    cat_index = {c: i for i, c in enumerate(categories)}
    if UNKNOWN not in cat_index:
        cat_index[UNKNOWN] = len(categories)

    # Phase 1: Keyword-Match
    by_keyword: dict[str, str] = {}
    unknown_items: list[str] = []
    for original in combined:
        category = classify_by_keyword(original, keywords, learned, categories)
        if category is not None:
            by_keyword[original] = category
        else:
            unknown_items.append(original)

    # Phase 2: ein einziger Bulk-LLM-Call
    llm_result: dict[str, str] = {}
    learned_new: dict[str, str] = {}
    if unknown_items and use_llm:
        llm_result = await classify_bulk_with_llm(
            hass, unknown_items, categories, agent_id
        )
        for original, category in llm_result.items():
            learned_new[original.lower()] = category

    # Phase 3: alles zusammenführen + sortieren
    classified: list[tuple[int, str, str]] = []
    for original in combined:
        category = (
            by_keyword.get(original)
            or llm_result.get(original)
            or UNKNOWN
        )
        idx = cat_index.get(category, cat_index[UNKNOWN])
        classified.append((idx, category, original))
    classified.sort(key=lambda x: (x[0], x[2].lower()))

    # Phase 4: nur die OFFENEN Keep-Items löschen, dann sortiert neu adden
    for it in keep_items:
        if _is_open(it) and it.get("summary"):
            await async_remove_item(hass, keep_entity, it["summary"])

    added: list[tuple[str, str]] = []
    completed_in_cookidoo: list[str] = []
    for _, category, original in classified:
        await async_add_item(hass, keep_entity, original)
        added.append((category, original))
        # Wenn das Item aus Cookidoo stammt: dort als erledigt markieren,
        # damit es beim nächsten Sync nicht erneut auftaucht.
        cookidoo_summary = cookidoo_originals.get(original.lower())
        if cookidoo_summary:
            await async_complete_item(hass, cookidoo_entity, cookidoo_summary)
            completed_in_cookidoo.append(cookidoo_summary)

    if learned_new:
        learned.update(learned_new)
        await async_save_learned(hass, entry_id, learned)

    _LOGGER.info(
        "Cookidoo→Keep Sync: %d sortiert geschrieben, %d in Cookidoo abgehakt, %d via LLM gelernt",
        len(added), len(completed_in_cookidoo), len(learned_new),
    )

    return {
        "added": added,
        "completed_in_cookidoo": completed_in_cookidoo,
        "learned": learned_new,
    }
