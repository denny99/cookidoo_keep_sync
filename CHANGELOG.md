# CHANGELOG


## v2.0.1 (2026-05-15)

### Bug Fixes

- Crash-safe sync with journal recovery, verify+retry stale deletes
  ([`f0adbbb`](https://github.com/denny99/cookidoo_keep_sync/commit/f0adbbb5b195fc276fff204fe195a6d6d73d0db9))

The sync previously deleted ALL Keep items before re-adding them. A crash between delete and re-add
  would permanently lose the entire shopping list.

- Sync journal persists desired state before destructive ops; next sync auto-recovers missing items
  if previous sync was interrupted. - Parallel deletes use return_exceptions=True (one failure won't
  abort batch). - Verify+retry step after deletes catches silently surviving items. -
  async_remove_item / async_add_item now log errors before re-raising. - Cookidoo completion moved
  to LAST phase (after Keep is fully updated).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>


## v2.0.0 (2026-04-26)

### Chores

- Defensive checks, i18n entity name, ci on develop branch
  ([`4c65423`](https://github.com/denny99/cookidoo_keep_sync/commit/4c65423e9f6f497cf35c042fc02505714b5b753a))

- Coordinator: explicit HomeAssistantError if run_sync is called for an unknown entry_id (was a
  silent KeyError before). - Skip-check extracted into a named helper for readability. - Categories
  todo entity uses translation_key + entity-translation files instead of a hardcoded German name. -
  pyproject.toml gets a comment explaining why the version is 0.0.0 (it's just tooling config, not a
  published package). - Test workflow now runs on develop pushes/PRs too, so the develop branch gets
  CI feedback without triggering releases. - Strip stray triple-blank lines.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

### Features

- Configurable LLM examples count, services.yaml hints, parser tests
  ([`3fdfc0e`](https://github.com/denny99/cookidoo_keep_sync/commit/3fdfc0eb7076dd40193c5828d94cc0706666fc42))

- New 'Advanced' options step exposes llm_examples_per_category (default 2, range 0-10). 0 disables
  the calibration block entirely. - services.yaml entry_id now has a real description that explains
  when it's needed and how to find the ID. - Extracted parse_bulk_response and extract_speech as
  pure public functions in classifier.py so the LLM-output parsing — the most fragile spot, since
  different conversation agents format replies differently — has direct unit-test coverage. - 14 new
  tests covering perfect format, whitespace, punctuation, case-insensitivity, fuzzy substring
  matching, hallucinated categories, out-of-range indices, partial responses and malformed
  speech-extraction shapes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

- New default categories, harden review-flagged spots
  ([`2c26f9f`](https://github.com/denny99/cookidoo_keep_sync/commit/2c26f9fb53a5970c5b51f2d8beeb986b971da251))

Behavior changes: - DEFAULT_CATEGORIES is now the curated 38-category list the user has been
  iterating on in production (Obst, Gemüse, Kartoffel, ... , Tiefkühlware, Saft, Getränke,
  Sonstiges). Replaces the original Rewe-style 14-category placeholder. - Service handlers now raise
  ServiceValidationError when called without entry_id and multiple configurations exist, instead of
  returning an empty result silently. - Quantities with unknown units preserve original casing in
  the output ('1 Tütchen + 2 Tütchen' → '3 Tütchen' instead of '3 tütchen').

Code quality: - Quantity dataclass renamed to _Quantity (private) and gained a unit_raw field to
  support the casing fix above. - coordinator.async_run_sync now returns a typed SyncResult
  TypedDict and uses a typed _CookidooGroup TypedDict instead of `dict[str, dict]`. - Removed dead
  CONF_LEARNED constant. - Promoted the lazy import of coordinator inside config_flow's
  async_step_learned to a top-level import (no circular dependency).

Tooling: - semantic-release now generates a CHANGELOG.md, excluding its own release commits.

Docs: - README updated to use the new English entity slug todo.cookidoo_keep_categories (no existing
  users to migrate).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v1.0.0 (2026-04-26)

### Refactoring

- Drop default keyword set
  ([`adaa012`](https://github.com/denny99/cookidoo_keep_sync/commit/adaa012eb121465880a0c71378c27cf1d5c72619))

Default keywords pointed at hardcoded category names ("Obst/Gemüse", "Tomaten Sachen", ...) but
  categories are user-editable via the auto-created todo entity. Once users renamed or restructured
  their categories, the defaults silently stopped matching anyway.

The LLM + learned cache make the keyword feature optional. Fresh installs now go straight to the LLM
  on first sync; everything is cached after that. Power users who want offline-only operation can
  still maintain keywords manually via the options flow — and now those keywords are guaranteed to
  match their actual categories because they wrote them themselves.

Existing users keep their previously-saved keyword config; this change only affects fresh installs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

- Drop keyword feature, send learned examples to LLM, fix dead code
  ([`eae2bd9`](https://github.com/denny99/cookidoo_keep_sync/commit/eae2bd99a2fe0fa3ed9b803db3e9b62bc1dbc4f8))

Behavior changes: - The keyword-substring matcher is gone. The LLM + persistent cache cover the same
  use cases, with the cache being checked first (instant), and the LLM only consulted for genuinely
  new items. The cache is editable via the options flow, so manual overrides still work — even for
  offline-only setups, the user just populates the cache themselves instead of curating keywords. -
  Bulk LLM calls now include up to 2 already-learned examples per category as calibration, so the
  LLM adopts the user's personal category schema and stops repeating earlier mistakes. - Removed
  CONF_CLEAR_BEFORE_SYNC: it was no longer wired up since the merge-and-rewrite refactor and was
  confusing dead UI.

Code quality: - Multi-entry service handler now resolves the target entry_id at call time (single
  registered entry → that one; multiple → require explicit entry_id). Previously the closure
  captured the first entry and ignored later ones. - Phase comments in the coordinator's run_sync
  are now numbered consistently (1..6 instead of overlapping 1, 2, 3a, 3b, 3, 4, 5...) -
  async_complete_item now catches HomeAssistantError specifically, not bare Exception. -
  _text_to_mapping has an explicit lowercase_keys flag instead of a hardcoded behavior tied to one
  caller. - Removed unused _LOGGER import in todo.py.

Docs: - README updated for the new flow (no more keyword references, quantity aggregation explained,
  cache editor mentioned). - services.yaml description rewritten.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.4.1 (2026-04-26)

### Bug Fixes

- Serialize cookidoo completes to avoid lost updates
  ([`8247164`](https://github.com/denny99/cookidoo_keep_sync/commit/8247164fc7aa27eca5a48b1e78ae06b8b9d26500))

The Cookidoo integration (miaucl/ha-cookidoo) loses ~90% of todo.update_item calls when they fire in
  parallel — a race somewhere on its API client. Switching the completes to sequential while keeping
  the keep-deletes parallel restores reliability.

Net cost: a few extra hundreds of milliseconds for the cookidoo completes phase, which is
  acceptable.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.4.0 (2026-04-26)

### Continuous Integration

- Bump checkout and setup-python to Node 24-compatible versions
  ([`35cd43d`](https://github.com/denny99/cookidoo_keep_sync/commit/35cd43d9de1c15f647958872f4635393ec6ccf61))

### Features

- Smarter classification + editable learned cache
  ([`87b90bf`](https://github.com/denny99/cookidoo_keep_sync/commit/87b90bf0bd637bb36ea41fe53d27d0431eb1be46))

Two improvements that together remove the need for hand-crafting tons of keyword specifiers like
  'edelsüß = Gewürze':

1. Items containing a comma (Cookidoo's variant syntax, e.g. "Paprika, edelsüß") now skip the
  keyword match entirely and go directly to the LLM. Substring matching is too primitive to handle
  these — "paprika" would always win, regardless of qualifier. Once the LLM classifies them, they
  are cached and resolved instantly on subsequent syncs.

2. The learned cache is now editable through the integration's options flow (Configure → Learned
  mappings). Manual entries override the LLM since the cache is checked before any classifier runs.

Also: classification now runs on the clean item name (without the appended " (qty)") so cache keys
  stay stable when only the quantity changes between syncs.

Tests for both behaviors added; classifier import made lazy so the pure functions are testable
  without HA installed.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.3.0 (2026-04-26)

### Bug Fixes

- Complete cookidoo items even when they are duplicates of existing keep items
  ([`eb1d7c7`](https://github.com/denny99/cookidoo_keep_sync/commit/eb1d7c7158fd74c3f9ab25b21cd9177e6424d4b0))

Previously the cookidoo completion path was tied to whether an item went through the add-to-keep
  loop. With the merge dedup logic, a cookidoo item that already existed in keep was deduped out of
  the add path and never completed in cookidoo, causing it to reappear on every subsequent sync.

Now every open cookidoo item is unconditionally queued for completion, keyed by UID (preferred, more
  reliable for todo.update_item) with summary fallback. Also upgraded the silent-fail log to WARNING
  so future issues are visible.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

### Features

- Aggregate quantities, add tests + semantic-release CI
  ([`23887e9`](https://github.com/denny99/cookidoo_keep_sync/commit/23887e915b4d3fa639b2153983baf23b5a77285b))

Cookidoo items with the same name (e.g. "Zwiebeln" appearing in two recipes with 70 g and 1 Stk) are
  now grouped, their quantities parsed and aggregated. Compatible units are converted (e.g. 800 g +
  0.5 kg = 1.3 kg, 1 EL + 2 TL = 1.67 EL). Incompatible units are shown side by side ("70 g + 1
  Stk"). The result is appended to the Keep entry as "Name (qty)".

Also handles deduplication with manually-added Keep entries: a Keep "Tomaten" and a Cookidoo
  "Tomaten (200 g)" are now treated as the same item (Cookidoo wins, carrying the quantity).

Add a real test suite (pytest, 57 tests) for the quantity parser and aggregator. Set up GitHub
  Actions: tests run on push/PR; on push to main, python-semantic-release auto-bumps the version in
  manifest.json and publishes a GitHub release based on Conventional Commits.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.2.0 (2026-04-26)

### Performance Improvements

- Parallelize keep-deletes + cookidoo-completes, skip when aligned
  ([`f3e03e9`](https://github.com/denny99/cookidoo_keep_sync/commit/f3e03e9c1654a37463bdd5ba05d0da700846dc0a))

- Run all keep removals and cookidoo completions concurrently via asyncio.gather. They are
  order-independent. - Add a skip path when the keep list is already in the desired order and there
  are no open cookidoo items left to copy. - When the order matches but cookidoo still has open
  items, only run the cookidoo completes (no needless keep clear+rewrite).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.1.0 (2026-04-26)

### Documentation

- Translate README to English, add AI-generated warning
  ([`88edf40`](https://github.com/denny99/cookidoo_keep_sync/commit/88edf407aa26226975c34f1e018c59c298870a9c))

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
