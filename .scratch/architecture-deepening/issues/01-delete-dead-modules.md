# Delete modules with no live callers

Status: ready-for-agent
Blocked by: none

Spec: [Implementation decision 1](../spec.md#1-delete-modules-with-no-live-callers-report-06).

Delete code that nothing live calls, so only the real Quote path is left to
deepen. No behaviour change.

## Backend

- `app/services/enhanced_price_service.py` (calls a CRUD function that no
  longer exists) and its only importer `app/api/endpoints/health.py` (never
  mounted in `main.py`).
- `app/services/api_error_handler.py`, `app/utils/graceful_degradation.py`,
  `app/core/error_responses.py`.
- Unused `StandardError` subclasses and unreachable handlers in
  `app/core/error_handling.py` (`handle_standard_error`,
  `handle_external_api_error`). Keep the registered handlers that live code
  reaches; the error response shape stays the same.
- Uncalled helpers in `crud_price_cache.py` / `crud_conversion_cache.py`
  (`get_cached_price`, `get_cached_prices_batch`,
  `get_cached_conversion_rates_batch`, the `ImportError` fallbacks).
- Uncalled `cache_management.py` methods (`get_cache_status_for_assets`,
  `get_cache_stats`, `clear_price_cache`, `clear_conversion_cache`,
  `get_cache_settings`, `get_cache_status`) and
  `optimized_cache_queries.get_cache_statistics_optimized`.
- `app/core/performance_monitoring.py` and its middleware and recording calls
  (write-only: nothing reads the metrics).
- `demo_service.start_cleanup_scheduler` / `stop_cleanup_scheduler` (never
  started; `scheduled_tasks` owns demo cleanup).

## Frontend

- `lib/services/apiWithRetry.ts`, `lib/utils/retryUtils.ts` if only it uses
  it, the `lib/services/index.ts` barrel, `cacheUtils.ts`, `cacheKeys.ts`.
- `performanceMonitoring.ts` and the lazy tracking import in `cacheService.ts`.
- Unreferenced components: `CacheManagementPanel`, `CurrentPrice`,
  `CacheIndicator`, `PageLoader`, `TableCellSkeleton`.
- `enhancedApi` `getAssetCacheInfo`, `getConversionCacheInfo`, `batch*`;
  `cacheOperations.getCachedConversionRate`.
- Empty `routes/wallets` and `routes/test-login` directories.
- Tests that only cover deleted code (the `batch*` tests in
  `enhancedApi.test.ts`; `cacheTracking.test.ts` if it only covers the
  deleted tracking).

## Done when

- A grep confirms zero live importers for each item before it is deleted;
  recheck this list against current code first.
- Backend `python -m pytest` passes; frontend unit tests, Svelte check and
  production build pass. No test of live behaviour changes except to drop
  imports of deleted code.
