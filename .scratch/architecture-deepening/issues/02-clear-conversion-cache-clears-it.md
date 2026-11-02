# "Clear conversion cache" clears the rate cache, and only it

Status: ready-for-agent
Blocked by: none

Spec: [Implementation decision 2](../spec.md#2-quote-cache-and-rate-cache-modules-report-01)
(the open bug, shipped on its own ahead of the cache modules).

`DELETE /api/v1/price/cache/conversions` calls
`cleanup_old_conversion_cache_entries(max_age_days=0)`. That function ignores
the argument and runs `cleanup_cache_optimized`, which deletes only rate
entries older than `CONVERSION_CACHE_CLEANUP_DAYS` and **also deletes old
Quote entries**. Same bug class as d587967 (price cache clear).

The frontend has a sibling bug: `enhancedApi.refreshAllPrices` and
`clearPriceCache` clear only the `stock_price_` and `crypto_price_` prefixes,
never `derivative_price_`.

## Expected

- The endpoint removes every rate cache entry, whatever its age, and no Quote
  cache entries. Response shape unchanged.
- Frontend price-cache clear and refresh-all also clear derivative Quotes.
- The scheduled cleanup keeps its age-based behaviour.

## Tests

- HTTP test next to the `test_clearing_price_cache_*` tests in
  `test_prices_conversions.py`: seed a fresh rate, an old rate and an old
  Quote; after the DELETE, no rates remain and the Quote remains. Write it
  first and see it fail.
- Frontend test through the existing `enhancedApi` interface that derivative
  Quotes are cleared.
