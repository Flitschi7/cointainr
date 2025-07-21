# Force Refresh Guide

This quick reference guide explains how to use the force refresh functionality in Cointainr to get the latest data when needed.

## What is Force Refresh?

Force refresh bypasses the cache and fetches fresh data directly from external APIs. Use this feature when you need the most up-to-date information, such as during volatile market conditions or when making important investment decisions.

## When to Use Force Refresh

Use force refresh in these situations:

- When you need the absolute latest price data
- Before making investment decisions
- When you suspect the cached data is outdated
- After significant market events
- When cache indicators show stale data (🔴)

## How to Force Refresh

### Global Refresh

To refresh all data in the application:

1. Click the refresh button (↻) in the top navigation bar
2. A loading indicator will appear while data is being fetched
3. Wait for the process to complete
4. All cache indicators should now show fresh data (🟢)

![Global Refresh Button](../images/global_refresh_button.png)

### Asset-Specific Refresh

To refresh a specific asset:

1. Locate the asset in your portfolio
2. Click the refresh icon (↻) next to the asset name
3. Only that asset's data will be refreshed

![Asset Refresh Button](../images/asset_refresh_button.png)

### Portfolio Refresh

To refresh your entire portfolio:

1. Go to the Portfolio page
2. Click the "Refresh Portfolio" button
3. All assets in your portfolio will be refreshed

![Portfolio Refresh Button](../images/portfolio_refresh_button.png)

### Conversion Rate Refresh

To refresh currency conversion rates:

1. Go to Settings > Currency
2. Click "Refresh Conversion Rates"
3. All conversion rates will be updated

![Conversion Refresh Button](../images/conversion_refresh_button.png)

## Force Refresh Options

When clicking the refresh button, you may see these options:

- **Standard Refresh**: Updates expired cache entries only
- **Force Refresh**: Updates all data regardless of cache status
- **Smart Refresh**: Updates critical data and expired cache entries

Choose the option that best fits your needs.

## Force Refresh from Context Menu

You can also force refresh specific components:

1. Right-click on any price display or chart
2. Select "Force Refresh" from the context menu
3. Only that component will be refreshed

## Keyboard Shortcuts

Use these keyboard shortcuts for faster refreshing:

- **F5**: Standard page refresh (uses cache)
- **Ctrl+F5** or **Cmd+F5**: Force refresh page and bypass browser cache
- **Alt+R**: Refresh portfolio data
- **Alt+C**: Refresh conversion rates

## Important Considerations

### API Rate Limits

Force refresh consumes API calls, which may be limited:

- **Finnhub.io**: 60 requests/minute
- **CoinGecko**: 50 requests/minute
- **Alpha Vantage**: 5 requests/minute

Excessive use of force refresh may cause you to hit these limits.

### Performance Impact

Force refresh may temporarily impact performance:

- The application may be slower while fetching fresh data
- Multiple simultaneous refreshes can cause higher CPU/memory usage
- Network bandwidth usage increases during refresh operations

### Batch Operations

For better performance when refreshing multiple assets:

1. Use the "Refresh All" button instead of refreshing individual assets
2. This optimizes API calls by batching requests
3. The operation may take longer but uses fewer API calls

## Troubleshooting Force Refresh

If force refresh doesn't seem to work:

1. **Check Network Connection**: Ensure you have internet connectivity
2. **API Status**: Check if external APIs are operational
3. **Rate Limits**: You may have hit API rate limits
4. **Browser Cache**: Try clearing your browser cache
5. **Wait and Retry**: Wait a few minutes and try again

## Best Practices

- **Use Sparingly**: Only force refresh when necessary
- **Schedule Updates**: Perform updates during off-peak hours
- **Batch Updates**: Refresh all data at once rather than individually
- **Check Indicators**: Look at cache indicators before refreshing
- **Monitor Usage**: Keep track of your API usage in Settings
