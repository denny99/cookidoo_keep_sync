"""Konstanten für Cookidoo → Keep Sync."""

DOMAIN = "cookidoo_keep_sync"

CONF_COOKIDOO_ENTITY = "cookidoo_entity"
CONF_KEEP_ENTITY = "keep_entity"
CONF_CATEGORIES_ENTITY = "categories_entity"  # optionaler Override
CONF_CONVERSATION_AGENT = "conversation_agent"
CONF_CATEGORIES = "categories"  # nur Fallback wenn keine Entity verfügbar
CONF_USE_LLM = "use_llm"

SERVICE_SYNC = "sync"
SERVICE_RESET_LEARNED = "reset_learned"

CATEGORIES_ENTITY_NAME = "Categories"  # Wird per translation_key lokalisiert
CATEGORIES_TRANSLATION_KEY = "categories"

# Default-Kategorien für neue User. User können diese in der auto-erstellten
# Todo-Entity per Drag & Drop sortieren / hinzufügen / entfernen.
DEFAULT_CATEGORIES: list[str] = [
    "Obst",
    "Gemüse",
    "Kartoffel",
    "Zwiebel",
    "Knoblauch",
    "Eier",
    "Frischware",
    "Brot",
    "Wurst",
    "Fleisch",
    "Milch",
    "Vegane Sahne",
    "Essig",
    "Öl",
    "Gewürze/Pfeffer",
    "Käse",
    "Butter",
    "Müsli",
    "Nudeln",
    "Backzutaten",
    "Reis",
    "Knödel",
    "Salz",
    "Frischkäse/Sahne",
    "Joghurt",
    "Konserven",
    "Pesto/Tomatenmark",
    "Asia/Exotisches",
    "Joghurt Drinks",
    "Hefe",
    "Süßigkeiten",
    "Reinigungsmittel",
    "Papiertücher/Klopapier",
    "Kinder Sachen",
    "Tiefkühlware",
    "Saft",
    "Getränke",
    "Sonstiges",
]
