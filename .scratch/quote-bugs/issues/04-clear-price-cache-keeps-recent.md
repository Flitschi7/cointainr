# "Clear price cache" keeps recent entries

Status: ready-for-agent

`DELETE /api/v1/price/cache` calls `cleanup_old_cache_entries(max_age_days=0)`,
but the optimized implementation ignores the argument and deletes only entries
older than `PRICE_CACHE_CLEANUP_DAYS` (default 30). It also deletes old
conversion rates, which the endpoint does not mention.

Pinned by `test_clearing_price_cache_keeps_recent_entries`.
