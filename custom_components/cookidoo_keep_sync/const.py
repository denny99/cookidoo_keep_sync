"""Konstanten für Cookidoo → Keep Sync."""

DOMAIN = "cookidoo_keep_sync"

CONF_COOKIDOO_ENTITY = "cookidoo_entity"
CONF_KEEP_ENTITY = "keep_entity"
CONF_CATEGORIES_ENTITY = "categories_entity"  # optionaler Override
CONF_CONVERSATION_AGENT = "conversation_agent"
CONF_CATEGORIES = "categories"  # nur Fallback wenn keine Entity verfügbar
CONF_KEYWORDS = "keywords"
CONF_LEARNED = "learned"
CONF_USE_LLM = "use_llm"
CONF_CLEAR_BEFORE_SYNC = "clear_before_sync"

CATEGORIES_ENTITY_NAME = "Cookidoo Keep Kategorien"

SERVICE_SYNC = "sync"
SERVICE_RESET_LEARNED = "reset_learned"

DEFAULT_CATEGORIES: list[str] = [
    "Obst/Gemüse",
    "Kartoffel/Zwiebel",
    "Brot/Eier/Frischware",
    "Wurst",
    "Fleisch",
    "Milch/Vegane Sahne",
    "Käse/Butter",
    "Müsli",
    "Nudeln und Backwaren",
    "Joghurt",
    "Tomaten Sachen",
    "Asia",
    "Saft",
    "Getränke",
    "Sonstiges",
]

# Keine Default-Keywords mehr: würden auf hartkodierte Kategoriennamen zeigen,
# die der User aber frei umbenennen kann. Erster Sync klassifiziert per LLM,
# alle Folgesyncs nutzen den persistenten learned-Cache.
# User kann im Options-Flow eigene Keywords pflegen — dann passend zu seinen
# eigenen Kategoriennamen.
DEFAULT_KEYWORDS: dict[str, str] = {}
