# Cointainr - Current Issues and Problems

## Overview

This document outlines the current issues found in the Cointainr codebase based on test results and architectural concerns.

## Test Results Summary

- **Total Tests**: 45 tests
- **Passed**: 28 tests (62%)
- **Failed**: 13 tests (29%)
- **Errors**: 4 tests (9%)

## Critical Issues

### 1. Excessive API Calls Problem ⚠️ **HIGH PRIORITY**

**Problem**: The application is making too many API calls, not respecting the caching strategy.

**Current Behavior**:

- API calls are being made on every component render
- Price refreshes happen automatically instead of only on manual "Force Refresh"
- Currency conversion calls are not properly cached
- Page reloads trigger new API calls instead of using cached data

**Expected Behavior**:

- **Only "Force Refresh" button should trigger new API calls**
- **Page reload should ONLY show cached prices**
- **Currency exchange rates should be cached based on ENV TTL settings**
- **New exchange rates only pulled when cache expires**

**Files Affected**:

- `frontend/src/routes/+page.svelte` - Page load triggers API calls
- `frontend/src/lib/components/ValueCell.svelte` - Makes API calls on render
- `frontend/src/lib/components/ProfitLossCell.svelte` - Makes API calls on render
- `frontend/src/lib/services/portfolioCalculations.ts` - Currency conversion logic

### 2. Missing API Endpoints (404 Errors)

**Failed Tests**:

```
FAILED tests/test_cache_api.py::TestCacheAPI::test_get_conversion_cache_stats - assert 404 == 200
FAILED tests/test_cache_api.py::TestCacheAPI::test_clear_price_cache - assert 404 == 200
FAILED tests/test_cache_api.py::TestCacheAPI::test_clear_conversion_cache - assert 404 == 200
FAILED tests/test_cache_api.py::TestCacheAPI::test_get_conversion_rate_respects_cache - assert 404 == 200
```

**Missing Endpoints**:

- `GET /cache/conversion/stats` - Conversion cache statistics
- `POST /cache/clear/prices` - Clear price cache
- `POST /cache/clear/conversion` - Clear conversion cache
- `GET /conversion/rate` - Currency conversion endpoint

### 3. Async/Await Issues

**Failed Tests**:

```
ERROR tests/test_cache_management_integration.py - TypeError: 'async_generator' object is not an iterator
FAILED tests/test_enhanced_conversion_service.py::test_conversion_service - async def functions are not natively supported
FAILED tests/test_inverse_cache.py::test_inverse_cache - async def functions are not natively supported
```

**Problems**:

- Integration tests trying to use `next(get_db())` on async generator
- Missing `@pytest.mark.asyncio` decorators on async test functions
- Database session handling in tests is incorrect

### 4. Cache Logic Failures

**Failed Tests**:

```
FAILED tests/test_cache_management.py::TestCacheManagementService::test_get_cache_status_for_assets_with_valid_cache - assert False is True
FAILED tests/test_cache_api.py::TestCacheAPI::test_get_crypto_price_respects_cache - assert True is False
FAILED tests/test_cache_api.py::TestCacheAPI::test_refresh_all_prices_respects_force_refresh - AssertionError: assert 'cached' in {...}
```

**Problems**:

- Cache validation logic not working correctly
- Force refresh not properly bypassing cache
- Cache status reporting incorrect values

### 5. Mock and Patching Issues

**Failed Tests**:

```
FAILED tests/test_price_cache_schema.py::TestPriceCacheReadSchema::test_get_cache_expiration_delegates_to_service - AttributeError: <module 'app.schemas.price_cache'> does not have the attribute 'cache_management_service'
FAILED tests/test_enhanced_price_service.py::TestEnhancedPriceService::test_get_stock_price_uses_valid_cache - AssertionError: Expected 'is_price_cache_valid' to be called once. Called 2 times.
```

**Problems**:

- Incorrect mock patching paths in tests
- Services being called multiple times when expected once
- Missing service dependencies in schema modules

## Architectural Issues

### 6. Currency Display and Caching Strategy

**Current Problem**:

- Prices are not consistently displayed in the currency selected in the "Add Asset" form
- Currency conversion happens on every render instead of using cached rates
- No proper TTL respect for currency exchange rates

**Required Fix**:

- Display prices in the currency specified when adding the asset
- Cache exchange rates with configurable TTL from environment variables
- Only refresh exchange rates when cache expires or force refresh is triggered

### 7. Frontend Performance Issues

**Problems**:

- Components making individual API calls instead of batch requests
- Sorting logic triggering unnecessary API calls
- No proper loading states during API calls
- Reactive statements causing excessive re-renders

### 8. Database and ORM Issues

**Problems**:

- Async/sync mismatch in database operations
- Incorrect session handling in tests
- Missing database connection pooling considerations

## Deprecation Warnings

**108 Warnings Total**, mainly:

```
DeprecationWarning: datetime.datetime.utcnow() is deprecated
DeprecationWarning: on_event is deprecated, use lifespan event handlers instead
```

**Files Affected**:

- `app/main.py` - FastAPI event handlers
- `app/services/cache_management.py` - DateTime usage
- `app/services/price_service.py` - DateTime usage
- `app/api/endpoints/price.py` - DateTime usage
- Multiple test files

## Action Items by Priority

### 🔴 Critical (Fix Immediately)

1. **Fix API call strategy** - Only allow force refresh to trigger new API calls
2. **Implement proper caching** - Page reloads should only use cached data
3. **Add missing API endpoints** - Complete the cache management API
4. **Fix currency conversion caching** - Respect TTL settings from environment

### 🟡 High Priority

1. **Fix async test issues** - Add proper pytest markers and database session handling
2. **Update deprecated datetime usage** - Use timezone-aware datetime objects
3. **Fix cache validation logic** - Ensure cache status is reported correctly
4. **Implement proper error handling** - For API failures and cache misses

### 🟢 Medium Priority

1. **Fix mock patching in tests** - Correct service dependency paths
2. **Update FastAPI event handlers** - Use lifespan events instead of on_event
3. **Improve test coverage** - Add integration tests for cache behavior
4. **Optimize database queries** - Reduce unnecessary database calls

### 🔵 Low Priority

1. **Code cleanup** - Remove unused imports and dead code
2. **Documentation** - Update API documentation
3. **Performance optimization** - Batch API requests where possible
4. **Logging improvements** - Add structured logging for debugging

## Environment Configuration Required

**Missing/Unclear Environment Variables**:

- `CONVERSION_CACHE_TTL_HOURS` - How long to cache exchange rates
- `PRICE_CACHE_TTL_MINUTES` - How long to cache price data
- `FORCE_REFRESH_ONLY` - Flag to disable automatic refreshes
- `DEFAULT_CURRENCY` - Default currency for price display

## Testing Strategy Improvements

1. **Add integration tests** for complete cache lifecycle
2. **Mock external API calls** to avoid hitting rate limits during testing
3. **Test cache expiration** scenarios thoroughly
4. **Add performance tests** to ensure API call limits are respected
5. **Test currency conversion** caching behavior specifically

## Next Steps

1. **Audit all API calls** in the frontend to identify unnecessary requests
2. **Implement cache-first strategy** for all price and conversion data
3. **Add proper loading states** and error handling
4. **Fix the failing tests** starting with the most critical ones
5. **Implement the missing API endpoints** for cache management
6. **Update the caching strategy** to respect user preferences and TTL settings

---

_Last Updated: July 17, 2025_
_Based on test run results and architectural analysis_
