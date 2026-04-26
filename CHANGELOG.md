# CHANGELOG


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
