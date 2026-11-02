# One valuation source for every dashboard view

Status: ready-for-agent
Blocked by: 05

Spec: [Implementation decision 5](../spec.md#5-one-valuation-source-report-03).

`portfolioCalculations` is correct but only feeds the table totals. These views
compute Value as `price × quantity` with no conversion (cash as raw quantity),
or treat failed conversions as 0:

- `TopHoldings.svelte`, `BrokerPieChart.svelte`, `AssetTypePieChart.svelte`,
  `AssetPerformanceChart.svelte` (also has `console.log [DEBUG]`),
  `PortfolioRiskScore.svelte`, `PortfolioEfficiency.svelte`.

## Decisions

- Valuation returns per-Holding results (Value, purchase cost, Gain/Loss,
  Return; each nullable for Unavailable; in the display currency) alongside
  the totals.
- The dashboard computes one valuation per (Holdings, Quotes, display
  currency, filter) and passes the per-Holding results to every view.
- Views never multiply or convert. Aggregates (per location, per asset type)
  sum per-Holding Values, skip Unavailable ones and mark the aggregate
  incomplete, as the totals already do.
- Remove the debug logging.
- Visual design unchanged.

## Tests

- Extend `portfolioCalculations.test.ts` with per-Holding results: mixed Quote
  currencies, cash in another currency, a Holding with no Quote →
  Unavailable.
- Browser smoke check with synthetic fixtures: Distribution and Analytics
  totals equal the table total for a mixed-currency portfolio.
