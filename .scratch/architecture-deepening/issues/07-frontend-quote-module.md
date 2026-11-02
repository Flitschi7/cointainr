# Frontend Quote module with a last-known-Quote offline store

Status: ready-for-agent
Blocked by: 04, 06

Spec: [Implementation decision 6](../spec.md#6-frontend-quote-module-report-04-depends-on-3-and-5).

Quotes are loaded three ways today: `+page.js` via `cacheOperations`;
`+page.svelte` via `PriceManagementService` → `enhancedApi` → deduplication →
`cacheService`; and components calling `enhancedApi` directly. Two Quote maps
are kept in sync reactively, and a localStorage cache copies the server TTLs.

## Decisions

- One module: `quotesFor(holdings, { force }) -> Map<holding id, Quote |
  Unavailable>` and `clear()` (calls the server clear endpoint, drops local
  state, covers every asset type).
- Inside: per-asset-type routing, merging concurrent requests for the same
  Quote, and a last-known-Quote store.
- The server decides staleness. Delete the client TTL copies and the client
  validity recomputation (`cacheStatus.ts` validity logic, `enhancedApi` TTL
  constants).
- Offline: last-known Quotes in localStorage, with no TTL, overwritten on
  every success. When a request fails, return the last known Quote marked
  stale with its original fetched-at time. Wrap every storage access, so
  blocked storage never breaks the dashboard.
- `+page.js`, `+page.svelte` and the views all use this module, with one Quote
  store. Absorb or delete `priceManagement.ts`, `cacheOperations.ts`,
  `cacheService.ts` and the Quote parts of `enhancedApi.ts`.
- HTTP stays in `api.ts`.

## Tests

- New tests with `fetch` stubbed: one request per Quote under concurrency,
  last-known Quote on failure, `clear()` clears derivatives, the server's
  stale flag passes through.
- Replace (don't layer on) `cacheService.test.ts` and the cache-key tests in
  `enhancedApi.test.ts`.
- Browser smoke check: the dashboard still renders Quotes with the server
  stopped after one successful load.
