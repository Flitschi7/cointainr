# Finnhub quote of 0 skips the Yahoo fallback and fails

Status: ready-for-agent

`PriceService.get_stock_price` falls back to Yahoo only when the Finnhub
price is `None`. Finnhub returns `c: 0` for unknown symbols, so Yahoo is never
tried; `currency` and `source` stay `None`, the cache schema rejects them, and
the endpoint answers 404 even when Yahoo has a quote.

Pinned by `test_stock_quote_of_zero_from_finnhub_skips_yahoo`.
