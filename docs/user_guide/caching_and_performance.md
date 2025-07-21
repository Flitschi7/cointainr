# Caching and Performance Guide

This guide explains how Cointainr uses caching to improve performance and reduce API calls, along with instructions for managing the cache and troubleshooting common issues.

## Table of Contents

1. [Understanding Cache Behavior](#understanding-cache-behavior)
2. [Cache Indicators](#cache-indicators)
3. [Force Refresh](#force-refresh)
4. [Troubleshooting](#troubleshooting)
5. [Frequently Asked Questions](#frequently-asked-questions)

## Understanding Cache Behavior

Cointainr uses a cache-first approach to minimize API calls and improve performance. Here's how it works:

### What Gets Cached

- **Price Data**: Current prices for stocks and cryptocurrencies
- **Conversion Rates**: Currency conversion rates between different currencies
- **Asset Information**: Basic asset details

### Cache Duration

By default, Cointainr caches data for the following durations:

- **Price Data**: 15 minutes
- **Conversion Rates**: 24 hours

These durations can be configured by your system administrator through environment variables.

### How Caching Works

1. When you load the application, Cointainr first checks if it has valid cached data
2. If valid cache exists, it displays the cached data immediately
3. If cache is expired or doesn't exist, it fetches fresh data from external APIs
4. The new data is then stored in the cache for future use

This approach provides several benefits:

- **Faster Loading**: Cached data loads instantly without waiting for API calls
- **Reduced API Usage**: Fewer API calls means you're less likely to hit rate limits
- **Offline Resilience**: Some data remains available even when external APIs are down

## Cache Indicators

Cointainr provides visual indicators to help you understand when you're viewing cached data:

### Status Icons

| Icon | Status | Description                                                                            |
| ---- | ------ | -------------------------------------------------------------------------------------- |
| 🟢   | Fresh  | Data was just fetched from the API                                                     |
| 🟡   | Cached | Valid cached data within TTL period                                                    |
| 🔴   | Stale  | Cached data that has expired but is still shown because fresh data couldn't be fetched |

### Cache Age

Next to each cached value, you'll see when the data was last updated:

- "2 minutes ago"
- "1 hour ago"
- "Just now"

### Cache Health Indicator

The global cache health indicator in the top navigation bar shows the overall status of your cache:

- **Green**: All data is fresh or within valid cache period
- **Yellow**: Some data is cached but still valid
- **Red**: Some data is stale (expired cache being used)

## Force Refresh

Sometimes you may want to bypass the cache and get the latest data from external APIs. Cointainr provides several ways to force a refresh:

### Refresh Button

The main refresh button in the top navigation bar will refresh all data:

1. Click the refresh icon (↻) in the top navigation bar
2. Wait for the refresh to complete
3. All data will be updated with fresh values from external APIs

### Asset-Specific Refresh

To refresh a specific asset:

1. Find the asset in your portfolio
2. Click the refresh icon (↻) next to the asset name
3. Only that asset's data will be refreshed

### Conversion Rate Refresh

To refresh currency conversion rates:

1. Go to Settings > Currency
2. Click "Refresh Conversion Rates"
3. All conversion rates will be updated

### Keyboard Shortcuts

- **F5** or **Ctrl+R**: Refresh the page (note: this uses cache for initial load)
- **Shift+F5** or **Ctrl+Shift+R**: Force refresh the page and bypass browser cache

## Troubleshooting

### Common Issues and Solutions

#### Stale Data

**Issue**: You see the red stale data indicator (🔴) next to prices.

**Solutions**:

1. Click the refresh button to force a refresh
2. Check your internet connection
3. Verify that the external APIs are operational (see Status page)
4. If the problem persists, try clearing the cache (Settings > Advanced > Clear Cache)

#### Inconsistent Prices

**Issue**: Prices seem inconsistent or don't match other sources.

**Solutions**:

1. Check when the data was last updated (cache age)
2. Force refresh to get the latest prices
3. Verify the price source in Settings > Data Sources

#### Slow Performance

**Issue**: The application is loading slowly.

**Solutions**:

1. Check your internet connection
2. Reduce the number of assets in your portfolio
3. Try clearing the browser cache
4. Disable any browser extensions that might interfere

#### API Rate Limit Errors

**Issue**: You see "API rate limit exceeded" errors.

**Solutions**:

1. Wait a few minutes before refreshing again
2. Reduce the frequency of manual refreshes
3. Contact your administrator to increase the rate limit if possible

### Cache Clearing

If you're experiencing persistent issues, you can clear the cache:

1. Go to Settings > Advanced
2. Click "Clear Price Cache" to clear only price data
3. Click "Clear Conversion Cache" to clear only conversion rates
4. Click "Clear All Cache" to clear everything

Note that clearing the cache will cause the next page load to be slower as fresh data is fetched.

## Frequently Asked Questions

### How often is data automatically refreshed?

Data is not automatically refreshed on a schedule. It's refreshed when:

- You load the application after the cache has expired
- You manually trigger a refresh
- You perform an action that requires fresh data

### Can I disable caching?

No, caching is a core feature of Cointainr that ensures good performance and respects API rate limits. However, you can always force a refresh when you need the latest data.

### Why do I see different prices than on other websites?

There are several possible reasons:

- You're viewing cached data (check the cache age indicator)
- Different websites use different data sources
- There might be a slight delay in price updates
- The price might include or exclude fees depending on the source

### How can I tell if I'm viewing cached data?

Look for the cache indicators next to the data:

- 🟢 Fresh data
- 🟡 Valid cached data
- 🔴 Stale cached data

### What happens if an external API is down?

If an external API is down:

1. Cointainr will use cached data if available (marked as stale if expired)
2. If no cache is available, you'll see an error message
3. The system will automatically retry the API call with exponential backoff

### Can I change how long data is cached?

Cache durations are configured by your system administrator through environment variables. Contact them if you need different cache settings.
