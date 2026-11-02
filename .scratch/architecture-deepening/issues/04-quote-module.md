# Quote module with a provider seam

Status: ready-for-agent
Blocked by: 03

Spec: [Implementation decision 3](../spec.md#3-quote-module-report-02-depends-on-2).

Replace `get_stock_price` / `get_crypto_price` / `get_derivative_price` and the
endpoint-level stale fallbacks with one Quote module:
`quote(asset_type, identifier, force_refresh) -> Quote{price, currency,
fetched_at, source, stale, age}`. It raises "Quote unavailable" only when no
provider and no cache entry has a Quote.

## Decisions

- Provider seam: each adapter answers "Quote for this identifier, or none".
  A Quote of 0 counts as none. Order per asset type: stock → Finnhub, then
  Yahoo (symbol and ISIN alike); crypto → CoinGecko; derivative → Onvista.
- The provider list is passed in (by the app at startup; by tests through the
  app's dependency setup), not read from module globals. Each provider has a
  real adapter and a fake adapter.
- One Finnhub adapter is shared with asset-name lookup in `assets.py`; delete
  the second `finnhub_client` in `price.py`.
- The stock, crypto and derivative routes and `/refresh-all` become thin
  adapters: Quote → existing JSON, "Quote unavailable" → existing 404. Delete
  their `except` stale-fallback blocks.
- Stale responses use the live shape (`cache_status` object) and keep the old
  flat fields (`cache_expired`, `cache_age_minutes`, `using_expired_cache`)
  with the same meaning for every asset type.
- Provider calls stay off the event loop.

## Tests

- First: pin that stale fallback returns the same response fields for stock,
  crypto and derivative (derivative's `using_expired_cache` differs today).
- Move `test_prices_conversions.py`, `test_responsiveness.py` and the Finnhub
  name-lookup patch in `test_holdings_crud.py` from monkeypatching
  `finnhub_client` / `yfinance.Ticker` / `httpx.AsyncClient` to fake adapters
  at the provider seam. Assertions stay the same.
