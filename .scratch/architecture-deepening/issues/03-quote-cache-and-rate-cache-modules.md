# Quote cache and rate cache modules

Status: ready-for-agent
Blocked by: 01, 02

Spec: [Implementation decision 2](../spec.md#2-quote-cache-and-rate-cache-modules-report-01).

Build two deep modules, a Quote cache and a rate cache, each owning its table,
key, TTL, freshness rule, timestamps and pruning. Absorb and delete
`cache_management.py`, `optimized_cache_queries.py`, `crud_price_cache.py` and
`crud_conversion_cache.py`.

## Interface (each cache; names may vary)

- `lookup(key) -> entry + stale + age`: expired entries come back marked
  stale, not hidden. The rate cache also tries the inverse pair.
- `store(key, value, currency, source)`
- `clear() -> count`: every entry of this cache only.
- `prune(now) -> count`: entries older than this cache's retention.
- `stats(now)`: fresh/stale counts and per-key status, using `lookup`'s rule.

## Rules

- Quote key: the identifier requested (ISIN, or upper-cased symbol).
- TTL and retention from existing settings (`PRICE_CACHE_TTL_MINUTES`,
  conversion TTL, `PRICE_CACHE_CLEANUP_DAYS`, `CONVERSION_CACHE_CLEANUP_DAYS`).
  No new settings, no new defaults.
- UTC timezone-aware inside the module; stored format unchanged (no
  migration).
- Freshness checks have no side effects (no hit/miss counters).

## Callers to switch

- Quote and rate lookups in `price_service` / `conversion_service`.
- `DELETE /cache`, `DELETE /cache/conversions` → `clear()`.
- `/cache/stats`, `/cache/conversions/stats`, `/cache/asset-status` →
  `stats()`; response shapes unchanged.
- `scheduled_tasks._cleanup_cache` → `prune()` once per cache, at most one
  VACUUM per run.
- `demo_service._cleanup_cache_tables` → `clear()` on both.

## Tests

- First, pin current behaviour of the stats and asset-status endpoints through
  HTTP (untested today).
- Prune through the cache interface directly (it has no HTTP route): entries
  just inside and just outside retention, for both caches.
- All existing Quote, rate and cache tests in `test_prices_conversions.py` and
  `test_responsiveness.py` pass unchanged.
