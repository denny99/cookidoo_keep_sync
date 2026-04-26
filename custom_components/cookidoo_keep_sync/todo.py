"""Todo-Plattform: stellt eine Kategorien-Liste zum Reordern in der HA-UI bereit."""
from __future__ import annotations

import uuid

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import (
    CATEGORIES_ENTITY_NAME,
    CATEGORIES_TRANSLATION_KEY,
    DEFAULT_CATEGORIES,
    DOMAIN,
)

STORAGE_VERSION = 1


def _store_key(entry_id: str) -> str:
    return f"{DOMAIN}_{entry_id}_categories"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store: Store = Store(hass, STORAGE_VERSION, _store_key(entry.entry_id))
    raw = await store.async_load()
    if not raw:
        raw = [
            {"uid": uuid.uuid4().hex, "summary": cat}
            for cat in DEFAULT_CATEGORIES
        ]
        await store.async_save(raw)

    entity = CategoriesTodoEntity(entry, store, raw)
    hass.data[DOMAIN][entry.entry_id]["categories_entity"] = entity
    async_add_entities([entity])


class CategoriesTodoEntity(TodoListEntity):
    """Eine Todo-Liste, deren Reihenfolge die Markt-Sortierung definiert."""

    _attr_has_entity_name = True
    _attr_name = CATEGORIES_ENTITY_NAME
    _attr_translation_key = CATEGORIES_TRANSLATION_KEY
    _attr_should_poll = False
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
    )

    def __init__(
        self, entry: ConfigEntry, store: Store, raw: list[dict]
    ) -> None:
        self._entry = entry
        self._store = store
        self._items: list[dict] = list(raw)
        self._attr_unique_id = f"{entry.entry_id}_categories"

    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            TodoItem(
                uid=it["uid"],
                summary=it["summary"],
                status=TodoItemStatus.NEEDS_ACTION,
            )
            for it in self._items
        ]

    def category_names(self) -> list[str]:
        """Liefert die Kategorien-Reihenfolge für den Sync-Coordinator."""
        return [it["summary"] for it in self._items if it.get("summary")]

    async def _persist(self) -> None:
        await self._store.async_save(self._items)
        self.async_write_ha_state()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        self._items.append(
            {"uid": item.uid or uuid.uuid4().hex, "summary": item.summary or ""}
        )
        await self._persist()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        for entry in self._items:
            if entry["uid"] == item.uid:
                if item.summary is not None:
                    entry["summary"] = item.summary
                break
        await self._persist()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        self._items = [it for it in self._items if it["uid"] not in uids]
        await self._persist()

    async def async_move_todo_item(
        self, uid: str, previous_uid: str | None = None
    ) -> None:
        moving = next((it for it in self._items if it["uid"] == uid), None)
        if not moving:
            return
        self._items.remove(moving)
        if previous_uid is None:
            self._items.insert(0, moving)
        else:
            for i, it in enumerate(self._items):
                if it["uid"] == previous_uid:
                    self._items.insert(i + 1, moving)
                    break
            else:
                self._items.append(moving)
        await self._persist()
