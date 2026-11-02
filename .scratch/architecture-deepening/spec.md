# Architecture deepening: Quotes, rates, valuation, sessions

Status: ready-for-agent

Turn the shallow, scattered modules around Quotes, rates, the caches behind
them, dashboard valuation and sessions into a few deep modules, and delete the
modules that have no live callers. Source: the architecture review of
2026-11-02 (candidates 01–07). Vocabulary follows [GLOSSARY.md](../../GLOSSARY.md);
architecture terms (module, interface, seam, adapter, depth, locality,
leverage) follow the codebase-design vocabulary. ADR-0001 (holdings-based
portfolio), ADR-0002 (floats for money) and ADR-0003 (container runs as root)
stand and are not touched.

## Problem Statement

As the person who maintains and uses Cointainr, I keep fixing the same kind of
bug in different places. In the last month, a Quote for an ISIN was cached
under the wrong key, a Finnhub Quote of 0 skipped the Yahoo fallback, expired
rates were not served when the rate API failed, and "clear price cache" did not
clear every entry. Each fix had to be applied to more than one module, because
the rules for Quotes, rates and staleness are spread across roughly eight
backend modules and five frontend modules, each holding its own copy of the
TTLs, cache keys and fallback order.

The same spread shows up on the dashboard. The table totals come from one
tested valuation module, but the Distribution and Analytics views compute
Value themselves as price × quantity without converting currencies, so they
disagree with the totals whenever Holdings have different Quote currencies.

Around this live code sit about 3,800 lines with no live callers: a second
price module, two error-handling frameworks, circuit breakers, a retrying
client and unused cache helpers. They look like real seams, which misleads
anyone (human or agent) trying to find where a Quote actually comes from.

There is also an open bug in this area: "clear conversion cache" runs the
7-day age-based cleanup instead of clearing the rate cache, and as a side
effect deletes old Quote cache entries. The frontend's "clear price cache"
also skips derivative Quotes.

## Solution

From the user's point of view nothing changes in how Holdings are entered or
how the app looks, except that numbers become consistent and cache controls do
what they say:

- Every dashboard view shows the same Value, Gain/Loss and Return for a
  Holding, in the display currency, with Unavailable shown as Unavailable
  rather than 0.
- "Clear price cache" and "clear conversion cache" clear exactly their own
  cache, completely, on both server and client.
- A Stale quote or stale rate is served with its age whenever a provider fails,
  the same way for every asset type and for rates.
- Loading the dashboard makes one rate request per currency pair rather than
  one conversion request per Holding.
- Signing out works the same whichever way the session token was sent.

Underneath, Quote fetching, the Quote cache, the rate cache, rates, frontend
Quote loading, valuation and sessions each become one deep module with a small
interface, and the dead modules are deleted first so only the live path is
left to deepen.

## User Stories

### Consistent valuation

1. As a portfolio owner, I want the Top Holdings list to show the same Value as the holdings table, so that I can trust either view.
2. As a portfolio owner, I want the location distribution chart to sum Values in the display currency, so that a location holding USD stocks and EUR cash is compared fairly.
3. As a portfolio owner, I want the asset type distribution chart to sum Values in the display currency, so that crypto and stock shares are not distorted by Quote currency.
4. As a portfolio owner, I want the performance chart to show Gain/Loss computed the same way as the table, so that I don't see two different Gain/Loss figures for one Holding.
5. As a portfolio owner, I want the risk score to be based on converted Values, so that it reflects my real exposure.
6. As a portfolio owner, I want the efficiency view to be based on converted Values, so that failed conversions don't silently count as unconverted amounts.
7. As a portfolio owner, I want a Holding whose Value is Unavailable to be shown as Unavailable in every view, so that I can tell missing data from a real zero.
8. As a portfolio owner, I want cash Holdings converted from their cash currency in every view, so that cash in another currency is not counted at face value.
9. As a portfolio owner, I want changing the display currency to update every view together, so that no view keeps old-currency numbers.
10. As a portfolio owner, I want filtering by location or asset type to apply the same valuation to every view, so that the filtered totals agree.

### Quotes

11. As a portfolio owner, I want a stock Quote to fall back from Finnhub to Yahoo when Finnhub has no Quote or quotes 0, so that a Holding still gets valued.
12. As a portfolio owner, I want the same fallback rule whether a stock is looked up by symbol or by ISIN, so that the lookup method doesn't change the outcome.
13. As a portfolio owner, I want a Stale quote served with its age when every provider fails, so that my portfolio still shows a Value offline.
14. As a portfolio owner, I want stock, crypto and derivative Quotes to report staleness in the same response shape, so that the UI shows age the same way for every asset type.
15. As a portfolio owner, I want "refresh all" to use exactly the same Quote rules as a single Quote request, so that a bulk refresh can't produce different results.
16. As a portfolio owner, I want a repeated Quote request within the refresh interval to make no provider call, so that I stay within provider rate limits.
17. As a portfolio owner, I want an ISIN Quote cached under the ISIN, so that repeated derivative lookups hit the cache.
18. As a portfolio owner, I want a 404 only when no provider and no cache has a Quote, so that "Unavailable" means genuinely unknown.
19. As a portfolio owner, I want slow providers not to block other requests, so that the dashboard stays responsive.
20. As a portfolio owner, I want asset-name lookup when adding a Holding to use the same Finnhub adapter as Quotes, so that there is one place configuring that provider.

### Rates

21. As a portfolio owner, I want an expired rate served, marked as from cache, when the rate API fails, so that conversions keep working offline.
22. As a portfolio owner, I want a 404 for a rate only when no rate is cached at all, so that "Unavailable" is honest.
23. As a portfolio owner, I want an inverse pair used when only the inverse rate is cached, so that I don't lose a conversion I could compute.
24. As a portfolio owner, I want the dashboard to fetch each currency pair's rate once and convert every Holding with it, so that loading is fast and doesn't flood the server.
25. As an existing API client, I want the current conversion endpoint to keep working with its current response, so that nothing that depends on it breaks.

### Caches

26. As a portfolio owner, I want "clear price cache" to remove every Quote cache entry on the server, so that the next request fetches fresh Quotes.
27. As a portfolio owner, I want "clear price cache" to leave rates alone, so that clearing one cache doesn't cost me the other.
28. As a portfolio owner, I want "clear conversion cache" to remove every rate cache entry, so that the button does what it says.
29. As a portfolio owner, I want "clear conversion cache" to leave Quote cache entries alone, so that clearing rates doesn't silently delete Quotes.
30. As a portfolio owner, I want "clear price cache" in the UI to clear derivative Quotes too, so that every asset type refreshes.
31. As a portfolio owner, I want the scheduled cleanup to prune old Quote and rate entries by their configured retention, once each per run, so that the database doesn't grow and no work is repeated.
32. As a portfolio owner, I want cache statistics to use the same freshness rule as Quote lookup, so that the stats match what the app does.
33. As a portfolio owner, I want per-Holding cache status to match the staleness shown next to its Quote, so that the indicators don't contradict each other.
34. As a self-hoster, I want the cache TTLs configured in one place on the server, so that changing an environment variable changes behaviour everywhere.
35. As a self-hoster, I want cache timestamps handled consistently, so that staleness is not off by a timezone offset.
36. As a demo-mode operator, I want the demo reset to clear caches through the same module as everything else, so that the reset can't drift from the real rules.

### Offline frontend

37. As a portfolio owner, I want the dashboard to show the last known Quotes when the server is unreachable, so that offline behaviour is preserved.
38. As a portfolio owner, I want the dashboard to load Quotes the same way on first load and on refresh, so that I don't see different results depending on how the page loaded.
39. As a portfolio owner, I want concurrent requests for the same Quote merged, so that opening the dashboard doesn't duplicate provider calls.

### Sessions

40. As a portfolio owner using authentication, I want logout to end my session whether the token came in a cookie, a Bearer header or the session-token header, so that signing out always works.
41. As a portfolio owner using authentication, I want the auth status endpoint to recognise every token source the middleware accepts, so that status and access agree.
42. As a portfolio owner using authentication, I want one session lookup per request, so that authenticated requests stay fast.
43. As a demo-mode operator, I want demo session cleanup to use the same rules as normal session expiry, so that demo resets don't leave orphaned or wrongly kept sessions.

### Maintainability

44. As a maintainer, I want one module that answers "what is the Quote for this asset", so that a Quote bug is fixed in one place.
45. As a maintainer, I want provider fallback order expressed as a per-asset-type list, so that adding or reordering a provider is a data change.
46. As a maintainer, I want modules with no live callers deleted, so that searching for the Quote path finds only the real one.
47. As a maintainer, I want one error response format for API errors, so that I don't have to learn three error frameworks.
48. As a maintainer, I want tests to pass fake providers in at a seam instead of patching module globals, so that tests survive internal refactors.
49. As a maintainer, I want tests to cross the same interface callers use, so that tests describe behaviour rather than implementation.
50. As an AI agent working on the repo, I want the Quote, rate, valuation and session logic each in one obvious module, so that I can find and change it without reading a dozen files.

## Implementation Decisions

Work is ordered so each step leaves the app working and tested. Later steps
depend on earlier ones as noted.

### 1. Delete modules with no live callers (report 06)

- Delete the second price module ("enhanced price service"), its only importer
  (the unmounted health router), the API error handler and graceful-degradation
  (circuit breaker) modules that only it used, and the unused error-responses
  module.
- Delete the unused Quote-cache and rate-cache helpers: batch lookups,
  single-entry lookup with no callers, the `ImportError` fallbacks around the
  optimized cleanup, and the cache-management methods with no callers.
- Delete the write-only backend performance-monitoring module and its
  middleware and recording calls, since nothing reads the metrics. (If metrics
  are wanted later, that is a new feature with a reader.)
- Frontend: delete the retrying API client, the unused services barrel and the
  cache utility/key modules only it exposed, the five unreferenced components
  (cache management panel, current price, cache indicator, page loader, table
  cell skeleton), the unused cache-info and batch functions, and the two empty
  route directories. Delete tests that only cover deleted functions.
- Keep the live core error handlers but delete the unused standard error
  subclasses and unreachable handlers; endpoints keep returning the current
  error response shape.
- Acceptance: every existing backend and frontend test that covers live
  behaviour passes unchanged; the production build and Svelte check pass.

### 2. Quote cache and rate cache modules (report 01)

- Build two deep modules, a **Quote cache** and a **rate cache**, each owning
  its table, cache key, TTL, freshness rule, timestamps and pruning.
- Interface of each (shape, names may vary):
  - `lookup(key) -> entry + stale flag + age`, returning an expired entry
    marked stale rather than hiding it; the caller decides nothing about
    staleness.
  - `store(key, value, currency, source)`.
  - `clear() -> count`: removes every entry of this cache only.
  - `prune(now) -> count`: removes entries older than this cache's configured
    retention.
  - `stats(now)`: counts of fresh/stale entries and per-key status, computed
    with the same freshness rule as `lookup`.
- The Quote cache key is the identifier the Quote was requested by (ISIN for
  derivatives and ISIN stock lookups, upper-cased symbol otherwise). The rate
  cache key is the currency pair; `lookup` also checks the inverse pair and
  returns the inverted rate.
- TTL and retention come from the existing environment settings
  (`PRICE_CACHE_TTL_MINUTES`, conversion TTL, `PRICE_CACHE_CLEANUP_DAYS`,
  `CONVERSION_CACHE_CLEANUP_DAYS`); no new settings, no changed defaults.
- All cache timestamps are handled as UTC timezone-aware values inside the
  module; stored values keep their current format so no migration is needed.
- Freshness checks no longer have side effects (no hit/miss counters inside
  the freshness check).
- Callers switch to these modules: Quote and rate endpoints, the cache-clear
  endpoints, the cache-stats and asset-status endpoints, the scheduled cleanup
  (calls `prune` once per cache per run, one VACUUM at most), and the demo
  reset (calls `clear` on both).
- Fixes the open bug: `DELETE /price/cache/conversions` calls the rate cache's
  `clear` and deletes every rate entry and no Quote entries.
- The remaining cache-management module, optimized cache queries module and
  the two cache CRUD modules are absorbed into the two cache modules and
  deleted.
- No schema change. API response shapes of all cache endpoints stay the same.

### 3. Quote module (report 02; depends on 2)

- Build one **Quote module** with interface `quote(asset_type, identifier,
  force_refresh) -> Quote` where Quote carries price, quote currency, fetched
  at, source, and a stale flag with age. It raises a single "Quote
  unavailable" error only when no provider and no cache entry has a Quote.
- Inside: identifier normalisation (ISIN vs symbol), Quote cache lookup,
  provider fallback, storing the result, and serving a stale entry when every
  provider fails. Stale fallback happens only here.
- Providers sit behind one provider seam: each provider adapter answers
  "Quote for this identifier, or none". A Quote of 0 or a missing Quote counts
  as none. Fallback order is a per-asset-type list: stock → Finnhub, then
  Yahoo (both for symbol and ISIN); crypto → CoinGecko; derivative → Onvista.
- Two adapters per provider justify the seam: the real HTTP/library adapter,
  and a fake used in tests. The provider list is passed into the Quote module
  (by the app at startup, by tests through the app's dependency setup), not
  read from module globals.
- One Finnhub adapter is shared by Quotes and asset-name lookup on Holding
  create/update; the second Finnhub client in the price router goes away.
- Quote endpoints and refresh-all become thin adapters that call the Quote
  module and map Quote → existing response JSON and "Quote unavailable" → the
  existing 404. The endpoint-level stale fallbacks are deleted.
- The response JSON for stock, crypto and derivative Quotes keeps every field
  it has today. The stale-fallback path, which currently returns a different
  shape, is aligned to the live shape (the `cache_status` object), and the
  old flat fields (`cache_expired`, `cache_age_minutes`, `using_expired_cache`)
  stay present with consistent meanings so existing clients keep working.
- Provider calls continue to run off the event loop, as today.

### 4. Rate module (report 05; depends on 2)

- Build one **rate module** with interface `rate(from, to, force_refresh) ->
  Rate{value, stale, age, source}`, raising "rate unavailable" only when the
  rate API fails and no rate (direct or inverse, any age) is cached.
- Stale-rate fallback moves from the endpoints into the rate module, matching
  the Quote module. The "any age" read is a rate cache `lookup`, not a huge
  max-age argument.
- The existing rate endpoint (`/rate/{from}/{to}`) and conversion endpoint
  (`/convert`) both call the rate module; `/convert` multiplies. Both keep
  their current response shape. The endpoint retry with `allow_expired` is
  deleted.
- The rate API sits behind the same kind of provider seam as Quotes (real
  adapter + fake adapter).
- Frontend valuation fetches the rate for each distinct (from, to) pair once
  per valuation and multiplies locally. The per-amount conversion cache and
  the amount-echo validation it required are removed; the rate response is
  still validated (positive, finite number).

### 5. One valuation source (report 03)

- The existing portfolio valuation module becomes the single source of Value,
  Gain/Loss and Return. Its interface grows to return per-Holding results
  (Value, purchase cost, Gain/Loss, Return, each nullable for Unavailable, all
  in the display currency) alongside the totals it returns today.
- The dashboard computes one valuation per (Holdings, Quotes, display
  currency, filter) and passes per-Holding results to every view: Top
  Holdings, location distribution, asset type distribution, performance chart,
  risk score and efficiency.
- Views stop multiplying price × quantity, stop calling currency conversion
  themselves, and render Unavailable as Unavailable. Views that need
  aggregates (per location, per asset type) sum the per-Holding Values, skipping
  Unavailable ones and marking the aggregate incomplete when any were skipped,
  consistent with how totals already work.
- Debug logging left in the performance chart is removed.

### 6. Frontend Quote module (report 04; depends on 3 and 5)

- Build one frontend **Quote module** with interface
  `quotesFor(holdings, { force }) -> Map<holding id, Quote | Unavailable>`, plus
  `clear()` that calls the server's clear endpoint and drops local state.
- Inside: per-asset-type request routing, merging concurrent requests for the
  same Quote, and a last-known-Quote store.
- Staleness is decided by the server only. The client stops computing
  validity from its own copies of the TTLs; the hard-coded TTL copies are
  deleted.
- Offline behaviour is preserved by a last-known-Quote store in localStorage:
  when a request fails, the last known Quote is returned marked stale with its
  original fetched-at time. It has no TTL of its own and is overwritten by
  every successful response. Reads and writes are wrapped so a blocked
  storage never breaks the dashboard.
- The page load function, the dashboard page and the views all get Quotes
  through this module. The duplicate Quote maps (page-level and price
  management) collapse into one store fed by this module. The price
  management service, the cache operations utility and the generic client
  cache are absorbed or deleted.
- `clear()` covers every asset type, including derivatives.
- The HTTP calls stay in the existing low-level API client; the Quote module
  depends on it, so tests can stub `fetch` as the valuation tests already do.

### 7. Session module (report 07)

- Build one **session module** with interface `session_from(request) ->
  Session | None` and `purge(now) -> count`.
- `session_from` accepts the cookie, a Bearer header and the session-token
  header, in that order, and performs one database lookup that both validates
  and returns session info.
- The auth middleware, the logout and status endpoints, and the demo reset all
  use it. The middleware stores the session on the request so endpoints don't
  look it up again. The unread `request.state.username` is removed.
- Demo session cleanup calls `purge` (or a `purge_all` for the demo reset)
  instead of raw deletes. The unused demo cleanup scheduler in the demo module
  is deleted; the scheduled-tasks module keeps the single demo cleanup loop.
- Login, credential checking (constant-time) and auth modes (off, on, demo) do
  not change.

### Contracts and data

- No database schema change and no migration.
- No change to any HTTP route path or to existing response fields. Fields are
  only added where a response becomes consistent (stale-fallback Quotes gain
  `cache_status`).
- No new environment variables; existing ones keep their defaults and meaning.

## Testing Decisions

- A good test drives behaviour through the interface that real callers use and
  asserts on what they observe: HTTP status and JSON, rendered or returned
  values, and which provider calls happened. It does not inspect cache keys,
  private helpers or table rows when an interface answer exists. Tests must
  survive the internal restructuring described above.
- **Seam 1 — the HTTP API (primary).** Quote, rate, cache-clear, cache-stats,
  asset-status, refresh-all, Holding create/update name lookup and auth
  behaviour are tested through the in-process ASGI client against a temporary
  SQLite database. Fake provider adapters (Finnhub, Yahoo, CoinGecko, Onvista,
  rate API) are passed in at the provider seam through the app's dependency
  setup, replacing today's monkeypatching of module globals. The no-network
  guard stays on.
- **Seam 2 — the Quote cache and rate cache interface,** used directly only
  for pruning, which has no HTTP route: entries just inside and just outside
  retention, both caches, one run prunes each cache once.
- **Frontend seam — the valuation module and the frontend Quote module with
  `fetch` stubbed,** as the valuation tests already do. Covers per-Holding
  results, one rate request per pair, Unavailable propagation, last-known
  Quote when `fetch` fails, merged concurrent requests and `clear()` covering
  derivatives. View components are not unit-tested; they only render
  per-Holding results.
- Tests to add first, before refactoring, pinning current correct behaviour
  and the open bugs:
  - `DELETE /price/cache/conversions` removes every rate entry and no Quote
    entries (fails today).
  - Cache-stats and asset-status endpoints report fresh/stale consistently with
    Quote lookup.
  - Stale fallback returns the same response shape for stock, crypto and
    derivative.
  - Logout and status recognise a session sent in the session-token header
    (fails today).
- Old tests that reach past the interface are replaced, not layered: the
  enhanced API tests that assert client cache keys and the direct client cache
  tests are deleted once the frontend Quote module tests exist.
- Prior art: the backend Quote/rate tests with fake providers, the
  responsiveness tests, holdings CRUD and validation tests, auth mode tests,
  error response tests, and the frontend portfolio valuation tests.
- Checks per step: backend `python -m pytest` in `backend/`; frontend unit
  tests, Svelte check and production build. Read the package scripts and test
  configuration before running them.

## Out of Scope

- Wallet sync (its own spec).
- A transaction ledger or realized gains (ADR-0001).
- Moving money to exact decimals (ADR-0002).
- Changing the container user (ADR-0003).
- New providers, new asset types, or changing which provider is used for an
  asset type.
- New metrics or monitoring endpoints to replace the deleted write-only
  performance monitoring.
- Visual redesign of the dashboard; views keep their look and only change
  where their numbers come from.
- Changes to the release workflow or CI beyond keeping the existing gates
  green.
- Removing the `/convert` endpoint.

## Further Notes

- Everything local is test data; the real installation runs on a separate
  server. Tests must never call a real provider or use a real key.
- Tickets (`Blocked by:` in each file):
  - [01 Delete modules with no live callers](issues/01-delete-dead-modules.md)
  - [02 "Clear conversion cache" clears the rate cache](issues/02-clear-conversion-cache-clears-it.md) (the open bug, ahead of the refactor)
  - [03 Quote cache and rate cache modules](issues/03-quote-cache-and-rate-cache-modules.md) (after 01, 02)
  - [04 Quote module with a provider seam](issues/04-quote-module.md) (after 03)
  - [05 Rate module](issues/05-rate-module.md) (after 03)
  - [06 One valuation source](issues/06-one-valuation-source.md) (after 05)
  - [07 Frontend Quote module](issues/07-frontend-quote-module.md) (after 04, 06)
  - [08 Session module](issues/08-session-module.md) (independent)
- Each step is a separate PR to `main` because it touches data access or
  persisted caches.
- Line counts for deleted modules come from the review and should be
  re-checked when the ticket is picked up.
