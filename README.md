# Cookidoo → Google Keep Sync

> ⚠️ **AI generated only** — This integration was written entirely by an AI assistant (Claude). It has not been manually reviewed line-by-line or extensively tested in the wild. Use at your own risk, expect rough edges, and please open issues / PRs if you hit problems.

A Home Assistant custom integration that synchronizes your **Cookidoo shopping list** to a **Google Keep list**, sorting items by your personal **supermarket category order**. Unknown items are classified by your configured **conversation agent** (e.g. Claude) in a single bulk call and learned for future syncs.

## Why?

When you import a recipe in Cookidoo, all ingredients land in its shopping list — but:

- the Cookidoo list is **read-only and not sortable**
- the order is whatever order the recipe mentions ingredients in — not the order you walk through the store

This integration solves both: it copies the items into a fully editable Google Keep list and sorts them in the order you actually shop.

## Features

- **Cookidoo → Keep merge & sort**: all open items from Cookidoo + everything you manually added in Keep are merged and sorted together
- **No double-imports**: after copying, the Cookidoo item is marked as completed there so it doesn't show up again on the next sync (assuming the Cookidoo integration supports `update_item`)
- **Already-checked items are ignored** in both lists
- **Sort by personal supermarket order** (e.g. fruit/veg → meat → cheese → drinks)
- **Keyword-based classification** (offline, free, ~90% hit rate)
- **Bulk LLM fallback** for unknown items: a single call to Claude / OpenAI / Ollama classifies all leftover items at once — structured `[N] Category` output is parsed via regex
- **Auto-learning**: every LLM-classified item is persisted and resolved by keyword match on the next sync — the LLM is only consulted for genuinely new items
- **Native HA Todo entity for the category order**: the integration auto-creates `todo.cookidoo_keep_kategorien` whose **order can be changed by drag & drop in the HA UI**
- Optional: override todo list, in case you want to maintain categories somewhere else (e.g. a Keep list shared with your partner)
- Service `cookidoo_keep_sync.sync` for buttons, automations, or voice commands

## Requirements

- Home Assistant ≥ 2024.6 (for the todo platform with reorder support)
- A **Cookidoo integration** that exposes a `todo` entity (e.g. [miaucl/ha-cookidoo](https://github.com/miaucl/ha-cookidoo))
- A **Google Keep integration** that exposes a `todo` entity (e.g. [watkins-matt/home-assistant-google-keep-sync](https://github.com/watkins-matt/home-assistant-google-keep-sync))
- *(Optional, recommended)* a **conversation integration**, e.g. the official Anthropic integration (Claude), OpenAI Conversation, Ollama, or Google Generative AI

## Installation

### Via HACS (recommended)

1. HACS → **Integrations** → three-dot menu → **Custom repositories**
2. Repository: `https://github.com/denny99/cookidoo_keep_sync`
3. Category: `Integration`
4. Add → search for **Cookidoo → Google Keep Sync** → install
5. Restart Home Assistant

### Manual

```bash
cd /config/custom_components
git clone https://github.com/denny99/cookidoo_keep_sync.git tmp
mv tmp/custom_components/cookidoo_keep_sync .
rm -rf tmp
```

Then restart Home Assistant.

## Setup

1. **Settings → Devices & Services → Add Integration → "Cookidoo → Google Keep Sync"**
2. Fill in the fields:
   - **Cookidoo shopping list (source)**: e.g. `todo.cookidoo_einkaufsliste`
   - **Google Keep list (target)**: e.g. `todo.google_keep_einkaufen`
   - **Conversation agent** *(optional)*: e.g. `conversation.claude`
   - **Enable LLM fallback**: recommended ✅
3. After confirming, the todo list **`todo.cookidoo_keep_kategorien`** is auto-created with default categories.

### ⚠️ Important: adjust the category order

The bundled default categories (e.g. "fruit/veg → potato/onion → … → drinks") match a specific Rewe store — **you'll almost certainly want to adjust them**. Here's how:

1. **Overview → Todo → `Cookidoo Keep Kategorien`**
2. Drag & drop items into the order you actually walk through your store
3. Add / remove items as you would for any todo list
4. The next sync respects the new order

You can also edit this list in Google Keep or other todo apps if you've configured your Keep-sync integration accordingly — the order is preserved.

## How do I trigger it?

The integration **doesn't add an automatic trigger** — you decide when a sync runs. Three recommended ways:

### 1. Dashboard button (simplest, "on demand")

Add a button card to your dashboard:

```yaml
type: button
name: Sort shopping list
icon: mdi:cart-arrow-right
show_state: false
tap_action:
  action: perform-action
  perform_action: cookidoo_keep_sync.sync
```

Tap the button: sync runs. Ideal right before going shopping.

### 2. Automation: sync on Cookidoo change

When Cookidoo writes new items into the shopping list (e.g. when a recipe is imported), the sync runs by itself:

```yaml
alias: "Cookidoo→Keep auto-sync"
description: Syncs whenever the Cookidoo list changes
mode: single
max_exceeded: silent
trigger:
  - platform: state
    entity_id: todo.cookidoo_einkaufsliste
    # Debounce: only trigger if no further change for 30s
    for: "00:00:30"
action:
  - service: cookidoo_keep_sync.sync
```

(`mode: single` plus the 30-second debounce prevents multiple syncs from running at once when items are added in rapid succession.)

### 3. Time-based (e.g. every morning before shopping)

```yaml
alias: "Cookidoo→Keep daily 09:00"
trigger:
  - platform: time
    at: "09:00:00"
action:
  - service: cookidoo_keep_sync.sync
```

### Voice command (Voice Assistant / Assist)

If you use **Claude (or another conversation agent)** as your Assist pipeline and "allow service calls" is enabled in the pipeline:

> *"Sort the shopping list"* → the agent calls `cookidoo_keep_sync.sync`.

You can make this more reliable by adding an HA intent script for it — see HA docs "Intent Scripts".

### Manual testing

**Developer Tools → Actions → `cookidoo_keep_sync.sync` → run**

Enable "return response" and you'll immediately see what was added, completed, and learned:

```yaml
added:
  - ["Obst/Gemüse", "Tomaten"]
  - ["Fleisch", "Hähnchenbrust"]
completed_in_cookidoo:
  - "Tomaten"
  - "Hähnchenbrust"
learned:
  hähnchenbrust: "Fleisch"
```

## How a sync works

```
1. Read all OPEN (unchecked) items from
     - the Cookidoo list
     - the Google Keep list
   and merge them into a deduplicated combined list.

2. Classify:
     a) Keyword match (offline, instant)            → e.g. fruit/veg
     b) On miss: bulk LLM call (one call for ALL    → "[N] Category"
        leftover items, parsed by regex)
     c) Otherwise: category "Sonstiges" (other)
   Every LLM-classified item is persisted to the learned cache.

3. Sort by category order from
     todo.cookidoo_keep_kategorien
   (drag & drop in the HA UI), alphabetically within a category.

4. Delete all OPEN Keep items, write the sorted list back.
   Already-checked Keep items are left untouched.

5. Cookidoo items we copied are marked completed in Cookidoo
   → no double-import on the next sync.
```

On subsequent syncs, learned items are resolved by the keyword-cache lookup — the LLM is only consulted for **genuinely new** items. So a sync with 30 known + 2 new items costs exactly one bulk call.

## Persistence / where is data stored?

| Data | Location | File |
|------|----------|------|
| **Learned item→category mappings** (LLM cache) | HA storage | `/config/.storage/cookidoo_keep_sync_<entry_id>_learned` |
| **Category order** (drag-and-drop list) | HA storage | `/config/.storage/cookidoo_keep_sync_<entry_id>_categories` |
| **Config flow data** (entity IDs, agent, keywords, options) | HA storage | `/config/.storage/core.config_entries` |

All persisted via HA's standard `Store` helper (atomic JSON writes). Survives restarts, HA upgrades, and is included in HA backups. In Docker setups the `/config` volume is typically mounted on the host, so caches survive container recreates.

## Configuration options

**Settings → Devices & Services → Cookidoo → Keep → Configure**

| Section | What you configure |
|---------|--------------------|
| **Lists & agent** | Source / target todo lists, conversation agent, optional override for the categories list |
| **Keyword mappings** | Add your own `keyword = Category` lines (extends defaults) |
| **Advanced** | Clear the Keep list before each sync (use with care!) |

The **category order** is **not** edited here, but directly in the todo entity (see above).

## Services

| Service | Description |
|---------|-------------|
| `cookidoo_keep_sync.sync` | Full sync. Optional `entry_id` parameter (when multiple configurations exist). Returns a response with `added`, `completed_in_cookidoo`, `learned`. |
| `cookidoo_keep_sync.reset_learned` | Clears the LLM-learned cache (e.g. when you renamed categories). |

## Privacy

- Items are sent only to **your configured** conversation agent.
- For a **local LLM** (e.g. Ollama), pick that as the conversation agent.
- No telemetry, no external calls beyond what your conversation agent does.

## Troubleshooting

**"Nothing in Keep after sync"**: check the logs (`Settings → System → Logs`, filter `cookidoo_keep_sync`). Most common cause: wrong entity IDs, or the Keep-sync integration can't (yet) write back.

**"LLM classifies into a non-existent category"**: the LLM occasionally returns a name that doesn't exactly match one of your categories. The integration falls back to fuzzy substring matching; if that also fails, the item lands in "Sonstiges". Fix: add an appropriate keyword rule, or rename the category slightly so the LLM picks it more reliably.

**"Order in Keep is wrong"**: the Keep-sync integration handles add-order differently across versions. If sort order isn't preserved, enable "Clear Keep list before each sync" in the Advanced tab.

## Limitations

- Sync is **one-way** (Cookidoo → Keep). What you check off or add in Keep is not pushed back to Cookidoo (and isn't possible anyway, Cookidoo is read-only).
- Duplicate detection is by **case-insensitive summary comparison** — slight wording differences are treated as separate items.

## Contributing

PRs welcome — especially for:
- Better default categories for other store chains
- More keyword mappings (please tag with region / store in the PR description)
- Translations

## License

MIT — see [LICENSE](LICENSE)

## Credits

- [miaucl/ha-cookidoo](https://github.com/miaucl/ha-cookidoo) for the Cookidoo integration
- [watkins-matt/home-assistant-google-keep-sync](https://github.com/watkins-matt/home-assistant-google-keep-sync) for the Google Keep integration
- Anthropic for Claude (for "why isn't Spätzle next to the noodles")
