# Expired conversion rate is not served when the rate API fails

Status: ready-for-agent

`ConversionService.get_conversion_rate` wraps every API failure in
`ValueError`. The `/api/v1/price/rate` and `/convert` endpoints map
`ValueError` to 404 before their expired-cache fallback branch runs, so an
expired cached rate is never returned when exchangerate-api is down. Prices
fall back to stale quotes; rates do not.

Pinned by `test_expired_rate_is_not_served_when_api_fails` in
`backend/tests/test_prices_conversions.py`.
