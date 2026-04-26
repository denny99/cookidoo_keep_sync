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

# keyword (lowercase substring) -> category name
DEFAULT_KEYWORDS: dict[str, str] = {
    # Obst/Gemüse
    "apfel": "Obst/Gemüse", "äpfel": "Obst/Gemüse", "banane": "Obst/Gemüse",
    "salat": "Obst/Gemüse", "gurke": "Obst/Gemüse", "paprika": "Obst/Gemüse",
    "möhre": "Obst/Gemüse", "karotte": "Obst/Gemüse", "brokkoli": "Obst/Gemüse",
    "zucchini": "Obst/Gemüse", "spinat": "Obst/Gemüse", "pilz": "Obst/Gemüse",
    "champignon": "Obst/Gemüse", "lauch": "Obst/Gemüse", "sellerie": "Obst/Gemüse",
    "kohl": "Obst/Gemüse", "blumenkohl": "Obst/Gemüse", "kürbis": "Obst/Gemüse",
    "beere": "Obst/Gemüse", "trauben": "Obst/Gemüse", "zitrone": "Obst/Gemüse",
    "limette": "Obst/Gemüse", "orange": "Obst/Gemüse", "avocado": "Obst/Gemüse",
    "ingwer": "Obst/Gemüse", "knoblauch": "Obst/Gemüse", "kräuter": "Obst/Gemüse",
    "petersilie": "Obst/Gemüse", "basilikum": "Obst/Gemüse",
    # Kartoffel/Zwiebel
    "kartoffel": "Kartoffel/Zwiebel", "zwiebel": "Kartoffel/Zwiebel",
    "schalotte": "Kartoffel/Zwiebel",
    # Brot/Eier/Frischware
    "brot": "Brot/Eier/Frischware", "brötchen": "Brot/Eier/Frischware",
    "eier": "Brot/Eier/Frischware",
    "spätzle": "Brot/Eier/Frischware", "gnocchi": "Brot/Eier/Frischware",
    "teig": "Brot/Eier/Frischware", "tortilla": "Brot/Eier/Frischware",
    "wraps": "Brot/Eier/Frischware", "tofu": "Brot/Eier/Frischware",
    # Wurst
    "wurst": "Wurst", "salami": "Wurst", "schinken": "Wurst", "speck": "Wurst",
    "aufschnitt": "Wurst",
    # Fleisch
    "hack": "Fleisch", "rind": "Fleisch", "schwein": "Fleisch",
    "hähnchen": "Fleisch", "huhn": "Fleisch", "pute": "Fleisch",
    "steak": "Fleisch", "geschnetzeltes": "Fleisch", "lachs": "Fleisch",
    "fisch": "Fleisch", "garnelen": "Fleisch",
    # Milch
    "milch": "Milch/Vegane Sahne", "sahne": "Milch/Vegane Sahne",
    "hafermilch": "Milch/Vegane Sahne", "sojamilch": "Milch/Vegane Sahne",
    # Käse/Butter
    "käse": "Käse/Butter", "butter": "Käse/Butter", "margarine": "Käse/Butter",
    "frischkäse": "Käse/Butter", "feta": "Käse/Butter", "mozzarella": "Käse/Butter",
    "parmesan": "Käse/Butter", "gouda": "Käse/Butter",
    # Müsli
    "müsli": "Müsli", "haferflocken": "Müsli", "cornflakes": "Müsli",
    "porridge": "Müsli",
    # Nudeln/Backwaren
    "nudel": "Nudeln und Backwaren", "spaghetti": "Nudeln und Backwaren",
    "penne": "Nudeln und Backwaren", "reis": "Nudeln und Backwaren",
    "mehl": "Nudeln und Backwaren", "zucker": "Nudeln und Backwaren",
    "backpulver": "Nudeln und Backwaren", "hefe": "Nudeln und Backwaren",
    "linsen": "Nudeln und Backwaren", "bohnen": "Nudeln und Backwaren",
    "kichererbsen": "Nudeln und Backwaren",
    # Joghurt
    "joghurt": "Joghurt", "jogurt": "Joghurt", "quark": "Joghurt",
    "skyr": "Joghurt", "pudding": "Joghurt",
    # Tomaten Sachen
    "passierte tomaten": "Tomaten Sachen", "tomatenmark": "Tomaten Sachen",
    "dosentomaten": "Tomaten Sachen", "tomatensauce": "Tomaten Sachen",
    "tomatensoße": "Tomaten Sachen", "ketchup": "Tomaten Sachen",
    # Asia
    "sojasauce": "Asia", "sojasoße": "Asia", "kokosmilch": "Asia",
    "currypaste": "Asia", "miso": "Asia", "wok": "Asia", "sushi": "Asia",
    "nori": "Asia", "sesam": "Asia",
    # Saft
    "saft": "Saft", "apfelschorle": "Saft",
    # Getränke
    "wasser": "Getränke", "bier": "Getränke", "wein": "Getränke",
    "cola": "Getränke", "limonade": "Getränke", "sprudel": "Getränke",
}
