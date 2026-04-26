"""Cookidoo → Google Keep Sync Integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CATEGORIES,
    CONF_KEYWORDS,
    DEFAULT_CATEGORIES,
    DEFAULT_KEYWORDS,
    DOMAIN,
    SERVICE_RESET_LEARNED,
    SERVICE_SYNC,
)
from .coordinator import async_run_sync, async_save_learned

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS: list[Platform] = [Platform.TODO]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    options = {**entry.data, **entry.options}
    options.setdefault(CONF_CATEGORIES, DEFAULT_CATEGORIES)
    options.setdefault(CONF_KEYWORDS, DEFAULT_KEYWORDS)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"options": options, "entry": entry}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_sync(call: ServiceCall) -> dict:
        target_entry_id = call.data.get("entry_id") or entry.entry_id
        return await async_run_sync(hass, target_entry_id)

    async def _handle_reset(call: ServiceCall) -> None:
        target_entry_id = call.data.get("entry_id") or entry.entry_id
        await async_save_learned(hass, target_entry_id, {})

    if not hass.services.has_service(DOMAIN, SERVICE_SYNC):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SYNC,
            _handle_sync,
            schema=vol.Schema({vol.Optional("entry_id"): str}),
            supports_response=SupportsResponse.OPTIONAL,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_LEARNED,
            _handle_reset,
            schema=vol.Schema({vol.Optional("entry_id"): str}),
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    options = {**entry.data, **entry.options}
    options.setdefault(CONF_CATEGORIES, DEFAULT_CATEGORIES)
    options.setdefault(CONF_KEYWORDS, DEFAULT_KEYWORDS)
    hass.data[DOMAIN][entry.entry_id]["options"] = options


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_SYNC)
        hass.services.async_remove(DOMAIN, SERVICE_RESET_LEARNED)
    return unload_ok
