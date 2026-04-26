"""Config- und Options-Flow für Cookidoo → Keep Sync."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_CATEGORIES_ENTITY,
    CONF_CONVERSATION_AGENT,
    CONF_COOKIDOO_ENTITY,
    CONF_KEEP_ENTITY,
    CONF_USE_LLM,
    DOMAIN,
)


def _todo_selector() -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain="todo"))


def _agent_selector() -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain="conversation"))


def _multiline() -> TextSelector:
    return TextSelector(TextSelectorConfig(multiline=True, type=TextSelectorType.TEXT))


def _mapping_to_text(d: dict[str, str]) -> str:
    return "\n".join(f"{k} = {v}" for k, v in sorted(d.items()))


def _text_to_mapping(text: str, *, lowercase_keys: bool = True) -> dict[str, str]:
    """Parst 'key = value'-Zeilen. Leere Zeilen und '#'-Kommentare werden ignoriert.
    Mit lowercase_keys=True (für den Lerncache) werden alle Keys auf Lowercase gezwungen."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if lowercase_keys:
            k = k.lower()
        if k and v:
            out[k] = v
    return out


class CookidooKeepConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_COOKIDOO_ENTITY]}__{user_input[CONF_KEEP_ENTITY]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Cookidoo → Keep",
                data=user_input,
                options={
                    CONF_USE_LLM: user_input.get(CONF_USE_LLM, True),
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_COOKIDOO_ENTITY): _todo_selector(),
                vol.Required(CONF_KEEP_ENTITY): _todo_selector(),
                vol.Optional(CONF_CONVERSATION_AGENT): _agent_selector(),
                vol.Optional(CONF_USE_LLM, default=True): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return CookidooKeepOptionsFlow(entry)


class CookidooKeepOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    @property
    def _current(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["entities", "learned"],
        )

    async def async_step_learned(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit den vom LLM gelernten Cache. Manuelle Einträge überschreiben
        was die KI sich gemerkt hat, weil der Cache vor jedem Klassifikator
        gecheckt wird."""
        from .coordinator import async_load_learned, async_save_learned

        if user_input is not None:
            new_learned = _text_to_mapping(user_input["text"])
            await async_save_learned(self.hass, self._entry.entry_id, new_learned)
            return self.async_create_entry(title="", data=self._entry.options)

        learned = await async_load_learned(self.hass, self._entry.entry_id)
        schema = vol.Schema(
            {
                vol.Required(
                    "text", default=_mapping_to_text(learned)
                ): _multiline(),
            }
        )
        return self.async_show_form(
            step_id="learned",
            data_schema=schema,
            description_placeholders={"count": str(len(learned))},
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        cur = self._current
        if user_input is not None:
            # Leere Werte für Optional-Felder rauswerfen, damit kein "None" persistiert wird
            cleaned = {
                k: v for k, v in user_input.items() if v not in (None, "")
            }
            for key in (CONF_CATEGORIES_ENTITY, CONF_CONVERSATION_AGENT):
                if key not in cleaned:
                    cleaned[key] = None
            return self.async_create_entry(
                title="",
                data={**self._entry.options, **cleaned},
            )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_COOKIDOO_ENTITY, default=cur.get(CONF_COOKIDOO_ENTITY)
                ): _todo_selector(),
                vol.Required(
                    CONF_KEEP_ENTITY, default=cur.get(CONF_KEEP_ENTITY)
                ): _todo_selector(),
                vol.Optional(
                    CONF_CATEGORIES_ENTITY,
                    description={"suggested_value": cur.get(CONF_CATEGORIES_ENTITY)},
                ): _todo_selector(),
                vol.Optional(
                    CONF_CONVERSATION_AGENT,
                    description={"suggested_value": cur.get(CONF_CONVERSATION_AGENT)},
                ): _agent_selector(),
                vol.Optional(
                    CONF_USE_LLM, default=cur.get(CONF_USE_LLM, True)
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="entities", data_schema=schema)
