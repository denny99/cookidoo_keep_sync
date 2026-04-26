"""Konstanten für Cookidoo → Keep Sync."""

DOMAIN = "cookidoo_keep_sync"

CONF_COOKIDOO_ENTITY = "cookidoo_entity"
CONF_KEEP_ENTITY = "keep_entity"
CONF_CATEGORIES_ENTITY = "categories_entity"  # optionaler Override
CONF_CONVERSATION_AGENT = "conversation_agent"
CONF_CATEGORIES = "categories"  # nur Fallback wenn keine Entity verfügbar
CONF_LEARNED = "learned"
CONF_USE_LLM = "use_llm"

CATEGORIES_ENTITY_NAME = "Categories"  # Wird per translation_key lokalisiert
CATEGORIES_TRANSLATION_KEY = "categories"

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

