# Stock quotes requested by ISIN never hit the cache

Status: ready-for-agent

For an ISIN resolved through Finnhub, the quote is cached under the resolved
symbol (e.g. `AAPL`), but lookups use the ISIN. Every ISIN request calls
Finnhub again, costing rate limit and ignoring `PRICE_CACHE_TTL_MINUTES`.

Pinned by `test_stock_isin_resolves_symbol_but_caches_under_symbol`.
