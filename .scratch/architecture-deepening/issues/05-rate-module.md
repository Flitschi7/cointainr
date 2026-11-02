# Rate module and one rate request per currency pair

Status: ready-for-agent
Blocked by: 03

Spec: [Implementation decision 4](../spec.md#4-rate-module-report-05-depends-on-2).

## Backend

- One rate module: `rate(from, to, force_refresh) -> Rate{value, stale, age,
  source}`. It raises "rate unavailable" only when the rate API fails and no
  direct or inverse rate of any age is cached.
- Stale fallback moves inside the module. Delete the `ValueError` →
  `allow_expired=True` retry in the `/convert` and `/rate/{from}/{to}` routes,
  and the `max_age_hours=999999` read.
- The rate API sits behind a provider seam (real and fake adapter), like
  Quotes.
- `/convert` and `/rate/{from}/{to}` both call the module; response shapes
  unchanged. `/convert` stays.

## Frontend

- Valuation fetches each distinct (from, to) pair once via the rate endpoint
  and multiplies locally.
- Remove the per-amount conversion cache (`conversion_${from}_${to}_${amount}`)
  and the amount-echo validation in `portfolioCalculations.convertAmount`;
  still check that the rate is a positive finite number.

## Tests

- Existing rate tests (including the offline expired-rate test) pass, moved to
  the fake adapter.
- `portfolioCalculations.test.ts`: two Holdings in USD and one in GBP, valued
  in EUR, make exactly two rate requests; a failed rate makes those Values
  Unavailable.
