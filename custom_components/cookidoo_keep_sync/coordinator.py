"""Sync-Logik: Cookidoo lesen → mit Keep mergen → klassifizieren → sortiert schreiben."""
from __future__ import annotations

import asyncio
import logging
from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store


class _CookidooGroup(TypedDict):
    name: str
    qtys: list[str]
    uids: list[str]


class SyncResult(TypedDict):
    added: list[tuple[str, str]]
    completed_in_cookidoo: list[str]
    learned: dict[str, str]
    skipped_no_changes: bool
    recovered: bool

from .classifier import UNKNOWN, classify_bulk_with_llm, classify_from_cache
from .quantities import aggregate as aggregate_qtys
from .quantities import normalize_for_dedup, split_name_qty, strip_qty_parens
from .const import (
    CONF_CATEGORIES,
    CONF_CATEGORIES_ENTITY,
    CONF_CONVERSATION_AGENT,
    CONF_COOKIDOO_ENTITY,
    CONF_KEEP_ENTITY,
    CONF_LLM_EXAMPLES_PER_CATEGORY,
    CONF_USE_LLM,
    DEFAULT_CATEGORIES,
    DEFAULT_LLM_EXAMPLES_PER_CATEGORY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
JOURNAL_STORAGE_VERSION = 1

# Im todo-Component-Standard: Status NEEDS_ACTION = offen, COMPLETED = abgehakt
STATUS_OPEN = "needs_action"


def storage_key(entry_id: str) -> str:
    return f"{DOMAIN}_{entry_id}_learned"


def _journal_key(entry_id: str) -> str:
    return f"{DOMAIN}_{entry_id}_sync_journal"


async def async_load_learned(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    store: Store = Store(hass, STORAGE_VERSION, storage_key(entry_id))
    data = await store.async_load()
    return data or {}


async def async_save_learned(
    hass: HomeAssistant, entry_id: str, learned: dict[str, str]
) -> None:
    store: Store = Store(hass, STORAGE_VERSION, storage_key(entry_id))
    await store.async_save(learned)


async def _save_journal(
    hass: HomeAssistant, entry_id: str, desired: list[str]
) -> None:
    """Persist desired Keep state before destructive operations."""
    store: Store = Store(hass, JOURNAL_STORAGE_VERSION, _journal_key(entry_id))
    await store.async_save({"desired_summaries": desired})


async def _load_journal(
    hass: HomeAssistant, entry_id: str
) -> list[str] | None:
    store: Store = Store(hass, JOURNAL_STORAGE_VERSION, _journal_key(entry_id))
    data = await store.async_load()
    if data and "desired_summaries" in data:
        return data["desired_summaries"]
    return None


async def _clear_journal(hass: HomeAssistant, entry_id: str) -> None:
    store: Store = Store(hass, JOURNAL_STORAGE_VERSION, _journal_key(entry_id))
    await store.async_save(None)


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
    try:
        await hass.services.async_call(
            "todo",
            "remove_item",
            {"entity_id": entity_id, "item": summary},
            blocking=True,
        )
    except HomeAssistantError as err:
        _LOGGER.warning("Konnte '%s' nicht aus %s entfernen: %s", summary, entity_id, err)
        raise


async def async_add_item(
    hass: HomeAssistant, entity_id: str, summary: str
) -> None:
    try:
        await hass.services.async_call(
            "todo",
            "add_item",
            {"entity_id": entity_id, "item": summary},
            blocking=True,
        )
    except HomeAssistantError as err:
        _LOGGER.error("Konnte '%s' nicht zu %s hinzufügen: %s", summary, entity_id, err)
        raise


async def async_complete_item(
    hass: HomeAssistant, entity_id: str, item_ref: str
) -> None:
    """Markiert ein Item als erledigt. `item_ref` darf UID oder Summary sein —
    manche Integrationen finden das Item nur per UID. Fehler werden nur geloggt."""
    try:
        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": entity_id,
                "item": item_ref,
                "status": "completed",
            },
            blocking=True,
        )
    except HomeAssistantError as err:
        _LOGGER.warning(
            "Konnte Item '%s' in %s nicht abhaken: %s",
            item_ref, entity_id, err,
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


def _is_keep_aligned(current: list[str], desired: list[str]) -> bool:
    """True wenn die offenen Keep-Items in genau dieser Reihenfolge bereits
    so dastehen, wie wir sie schreiben würden (case-insensitiv)."""
    return [s.lower() for s in current] == [s.lower() for s in desired]


async def _recover_from_journal(
    hass: HomeAssistant, entry_id: str, keep_entity: str
) -> bool:
    """Check for an interrupted previous sync and restore the desired Keep state."""
    journal = await _load_journal(hass, entry_id)
    if journal is None:
        return False

    keep_items = await async_get_todo_items(hass, keep_entity)
    current = {
        (it.get("summary") or "").strip()
        for it in keep_items
        if _is_open(it) and it.get("summary")
    }
    missing = [s for s in journal if s not in current]
    if not missing:
        _LOGGER.info("Sync-Journal gefunden, aber Keep ist vollständig — Journal wird gelöscht")
        await _clear_journal(hass, entry_id)
        return False

    _LOGGER.warning(
        "Vorheriger Sync wurde unterbrochen! %d Items fehlen in Keep — stelle wieder her",
        len(missing),
    )
    for summary in missing:
        try:
            await async_add_item(hass, keep_entity, summary)
        except HomeAssistantError as err:
            _LOGGER.error("Recovery: konnte '%s' nicht wiederherstellen: %s", summary, err)
    await _clear_journal(hass, entry_id)
    return True


async def async_run_sync(hass: HomeAssistant, entry_id: str) -> SyncResult:
    """Mergt Cookidoo + offene Keep-Items, klassifiziert, schreibt sortiert."""
    if entry_id not in hass.data.get(DOMAIN, {}):
        raise HomeAssistantError(
            f"cookidoo_keep_sync: kein aktiver Entry mit ID {entry_id!r}"
        )
    data = hass.data[DOMAIN][entry_id]
    options = data["options"]

    cookidoo_entity: str = options[CONF_COOKIDOO_ENTITY]
    keep_entity: str = options[CONF_KEEP_ENTITY]
    agent_id: str | None = options.get(CONF_CONVERSATION_AGENT)
    categories = await _resolve_categories(hass, entry_id, options)
    use_llm: bool = options.get(CONF_USE_LLM, True) and bool(agent_id)
    # NumberSelector persists floats; slicing needs a real int.
    llm_examples_per_cat = int(
        options.get(
            CONF_LLM_EXAMPLES_PER_CATEGORY, DEFAULT_LLM_EXAMPLES_PER_CATEGORY
        )
    )

    learned: dict[str, str] = await async_load_learned(hass, entry_id)

    recovered = await _recover_from_journal(hass, entry_id, keep_entity)

    try:
        cookidoo_items = await async_get_todo_items(hass, cookidoo_entity)
    except HomeAssistantError as err:
        _LOGGER.warning(
            "Cookidoo-Entity %s nicht erreichbar, sync läuft nur auf Keep: %s",
            cookidoo_entity, err,
        )
        cookidoo_items = []
    keep_items = await async_get_todo_items(hass, keep_entity)

    # Phase 1: Cookidoo-Items mit gleichem Namen gruppieren und Mengen aggregieren.
    # Quantity-Quelle: bevorzugt das description-Feld der Todo-Item, sonst Trailing-Qty
    # aus dem Summary parsen (z.B. "Zwiebeln 70 g").
    cookidoo_groups: dict[str, _CookidooGroup] = {}  # lower(name) -> group
    for it in cookidoo_items:
        if not _is_open(it):
            continue
        raw_summary = (it.get("summary") or "").strip()
        if not raw_summary:
            continue
        desc = (it.get("description") or "").strip()
        if desc:
            name, qty = raw_summary, desc
        else:
            name, qty = split_name_qty(raw_summary)
        key = name.lower()
        g = cookidoo_groups.setdefault(key, {"name": name, "qtys": [], "uids": []})
        if qty:
            g["qtys"].append(qty)
        g["uids"].append(it.get("uid") or raw_summary)

    cookidoo_summaries: list[str] = []
    cookidoo_to_complete: list[str] = []
    for key, g in cookidoo_groups.items():
        qty_str = aggregate_qtys(g["qtys"])
        final = f"{g['name']} ({qty_str})" if qty_str else g["name"]
        cookidoo_summaries.append(final)
        cookidoo_to_complete.extend(g["uids"])

    # Phase 2: Mit offenen Keep-Items mergen. Dedup vergleicht Namen ohne
    # Klammer-Zusatz, damit Cookidoo "Zwiebeln (70 g)" das Keep-"Zwiebeln" ersetzt.
    seen: set[str] = set()
    combined: list[str] = []

    def _push(summary: str) -> None:
        s = summary.strip()
        if not s:
            return
        key = normalize_for_dedup(s)
        if key in seen:
            return
        seen.add(key)
        combined.append(s)

    for s in cookidoo_summaries:
        _push(s)
    for it in keep_items:
        if _is_open(it):
            _push(it.get("summary") or "")

    cat_index = {c: i for i, c in enumerate(categories)}
    if UNKNOWN not in cat_index:
        cat_index[UNKNOWN] = len(categories)

    # Klassifizierung läuft auf dem CLEAN-Namen (ohne unseren " (qty)"-Anhang),
    # damit Cache-Keys stabil bleiben, wenn sich nur die Menge ändert.
    clean_for: dict[str, str] = {original: strip_qty_parens(original) for original in combined}

    # Phase 3a: Lerncache prüfen
    by_cache: dict[str, str] = {}
    unknown_items: list[str] = []  # Liste der CLEAN-Namen (deduped)
    for original in combined:
        clean = clean_for[original]
        category = classify_from_cache(clean, learned, categories)
        if category is not None:
            by_cache[original] = category
        elif clean not in unknown_items:
            unknown_items.append(clean)

    # Phase 3b: ein einziger Bulk-LLM-Call für unbekannte Items.
    # Bisherige Cache-Einträge gehen als Beispiele an den LLM mit, damit
    # er das Schema des Users übernimmt und nicht wieder Fehler wie
    # "Paprika, edelsüß → Obst/Gemüse" macht.
    llm_result: dict[str, str] = {}
    learned_new: dict[str, str] = {}
    if unknown_items and use_llm:
        llm_result = await classify_bulk_with_llm(
            hass,
            unknown_items,
            categories,
            agent_id,
            learned=learned,
            examples_per_category=llm_examples_per_cat,
        )
        for clean, category in llm_result.items():
            learned_new[clean.lower()] = category

    # Phase 4: alles zusammenführen + sortieren
    classified: list[tuple[int, str, str]] = []
    for original in combined:
        clean = clean_for[original]
        category = (
            by_cache.get(original)
            or llm_result.get(clean)
            or UNKNOWN
        )
        idx = cat_index.get(category, cat_index[UNKNOWN])
        classified.append((idx, category, original))
    classified.sort(key=lambda x: (x[0], x[2].lower()))
    desired_summaries = [original for _, _, original in classified]

    # Phase 5: Skip-Check — wenn Keep bereits exakt diese Liste in dieser
    # Reihenfolge zeigt UND keine offenen Cookidoo-Items rumliegen, ist nichts zu tun.
    current_open_keep = [
        (it.get("summary") or "").strip()
        for it in keep_items
        if _is_open(it) and it.get("summary")
    ]
    keep_aligned = _is_keep_aligned(current_open_keep, desired_summaries)
    nothing_to_do = keep_aligned and not cookidoo_to_complete

    added: list[tuple[str, str]] = []
    completed_in_cookidoo: list[str] = []

    if nothing_to_do:
        _LOGGER.info("Cookidoo→Keep Sync: nichts zu tun (Liste bereits aktuell)")
    else:
        # Phase 6: Safe sync — journal-protected delete→add→complete.
        #
        # Before any destructive operation, persist the desired Keep state
        # to a journal. If the process crashes mid-sync, the next sync
        # detects the journal and restores missing items.
        if not keep_aligned:
            await _save_journal(hass, entry_id, desired_summaries)

        # Phase 6a: Delete open Keep items in parallel.
        # return_exceptions=True ensures ALL deletes are attempted even if
        # some fail — a single network error won't abort the batch.
        if not keep_aligned and current_open_keep:
            results = await asyncio.gather(
                *[async_remove_item(hass, keep_entity, s) for s in current_open_keep],
                return_exceptions=True,
            )
            failures = [
                (s, r) for s, r in zip(current_open_keep, results)
                if isinstance(r, BaseException)
            ]
            if failures:
                _LOGGER.warning(
                    "Keep-Sync: %d/%d Deletes fehlgeschlagen: %s",
                    len(failures), len(current_open_keep),
                    ", ".join(f"'{s}'" for s, _ in failures),
                )

            # Verify: re-fetch Keep and retry any items that survived.
            # The Keep integration sometimes reports success but the item
            # stays — a sequential retry usually clears them.
            still_there = await async_get_todo_items(hass, keep_entity)
            stale = [
                (it.get("summary") or "").strip()
                for it in still_there
                if _is_open(it) and it.get("summary")
            ]
            if stale:
                _LOGGER.warning(
                    "Keep-Sync: %d Items überlebten paralleles Löschen, versuche erneut: %s",
                    len(stale), ", ".join(f"'{s}'" for s in stale),
                )
                for s in stale:
                    try:
                        await async_remove_item(hass, keep_entity, s)
                    except HomeAssistantError:
                        _LOGGER.warning("Retry-Delete für '%s' fehlgeschlagen", s)

        # Phase 6b: Re-add items in sorted order (sequential for ordering).
        if not keep_aligned:
            for _, category, original in classified:
                await async_add_item(hass, keep_entity, original)
                added.append((category, original))

        # Phase 6c: Clear journal — Keep is now in the desired state.
        if not keep_aligned:
            await _clear_journal(hass, entry_id)

        # Phase 6d: Cookidoo-Completes LAST — only after Keep is fully updated.
        # Sequential because parallel update_item calls on ha-cookidoo lose
        # updates (race on the Cookidoo API client).
        # Errors are logged per-item (async_complete_item has its own try/except).
        if cookidoo_to_complete:
            try:
                for ref in cookidoo_to_complete:
                    await async_complete_item(hass, cookidoo_entity, ref)
                completed_in_cookidoo = list(cookidoo_to_complete)
            except HomeAssistantError as err:
                _LOGGER.warning(
                    "Cookidoo-Completes übersprungen (%s nicht erreichbar): %s",
                    cookidoo_entity, err,
                )

    if learned_new:
        learned.update(learned_new)
        await async_save_learned(hass, entry_id, learned)

    _LOGGER.info(
        "Cookidoo→Keep Sync: %d sortiert, %d in Cookidoo abgehakt, %d via LLM gelernt%s",
        len(added), len(completed_in_cookidoo), len(learned_new),
        " (nach Recovery)" if recovered else "",
    )

    return {
        "added": added,
        "completed_in_cookidoo": completed_in_cookidoo,
        "learned": learned_new,
        "skipped_no_changes": nothing_to_do,
        "recovered": recovered,
    }
