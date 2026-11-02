# Bug cleanup: quotes, rates, cache, and password check

Status: ready-for-agent

Fix the four quote and cache bugs found while writing backend tests (item 06 of
[app-optimization](../app-optimization/spec.md)), plus the plain `==` password
check. Each bug is already pinned by a test that asserts the current, wrong
behavior. Fixing a bug means flipping its pinned test to assert the expected
behavior below.

Vocabulary follows [GLOSSARY.md](../../GLOSSARY.md).

## Context

- The real installation runs on a separate server and pulls
  `ghcr.io/flitschi7/cointainr:latest` manually. Everything local is test data.
- Backend tests run with `python -m pytest` in `backend/`, against a temporary
  SQLite file with mocked providers (Finnhub, Yahoo, exchangerate-api). No test
  may call a real provider or use a real key.
- Sessions come from `get_db` / `session_scope()` in `app/db/database.py`.

## Decisions

- **Offline rates behave like offline quotes.** When the rate API fails and an
  expired rate is cached, serve the expired rate (marked as from cache) instead
  of a 404. A 404 is right only when no rate is cached at all.
- **A quote of 0 counts as no quote.** Finnhub answers `c: 0` for unknown
  symbols, so a 0 from Finnhub moves on to Yahoo, the same as `None`. If Yahoo
  also has nothing, the endpoint answers 404 as today.
- **ISIN quotes are cached under the ISIN they were asked for.** A repeated
  request for the same ISIN within `PRICE_CACHE_TTL_MINUTES` makes no provider
  call. Requests by symbol keep working as before.
- **"Clear price cache" clears the price cache.** `DELETE /api/v1/price/cache`
  removes every price cache entry, whatever its age. It leaves conversion rates
  alone. The scheduled cleanup keeps its age-based behavior
  (`PRICE_CACHE_CLEANUP_DAYS`, `CONVERSION_CACHE_CLEANUP_DAYS`).
- **Constant-time credential check.** `AuthService.validate_credentials`
  compares username and password with `secrets.compare_digest` on UTF-8 bytes.
  Results for valid, wrong, and empty credentials stay the same.

## Work items

One PR for all five, one commit per item, no `[feat]` tag (patch release).

| #   | Item                                                                                       | Pinned test                                                 |
| --- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| 01  | [Expired rate served when the rate API fails](issues/01-expired-rate-not-served-offline.md) | `test_expired_rate_is_not_served_when_api_fails`            |
| 02  | [Finnhub 0 falls back to Yahoo](issues/02-zero-finnhub-quote-skips-yahoo.md)               | `test_stock_quote_of_zero_from_finnhub_skips_yahoo`         |
| 03  | [ISIN quotes hit the cache](issues/03-isin-quote-never-hits-cache.md)                      | `test_stock_isin_resolves_symbol_but_caches_under_symbol`   |
| 04  | [Clear price cache removes all price entries](issues/04-clear-price-cache-keeps-recent.md) | `test_clearing_price_cache_keeps_recent_entries`            |
| 05  | [Constant-time password check](issues/05-constant-time-password-check.md)                  | none yet; add to `test_auth_modes.py`                       |

### Acceptance checks

- Each pinned test is renamed and rewritten to assert the expected behavior,
  fails on the old code, and passes on the fix.
- **01**: with an expired cached rate and a failing rate API, `/price/rate` and
  `/price/convert` answer 200 with the cached rate; with no cached rate, 404.
- **02**: Finnhub 0 and Yahoo quote → 200 from Yahoo; both empty → 404.
- **03**: two requests for the same ISIN inside the TTL → one Finnhub quote
  call; the second response comes from the cache.
- **04**: after the call, no price cache rows remain; conversion rate rows are
  unchanged; the reported count matches the rows removed.
- **05**: existing auth-mode tests pass unchanged; `validate_credentials` no
  longer uses `==` on the password.
- The full backend suite passes, and CI is green on the PR.

## Out of scope

- Other provider behavior (CoinGecko, Onvista), quotas, and cache TTLs.
- Changing the scheduled cleanup or the cache schema.
- Login rate limiting or password hashing.
