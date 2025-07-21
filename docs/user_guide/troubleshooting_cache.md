# Troubleshooting Cache Issues

This guide provides detailed steps for diagnosing and resolving cache-related issues in Cointainr.

## Diagnosing Cache Problems

### Cache Status Check

First, check the current status of your cache:

1. Go to Settings > Advanced > Cache Status
2. Review the following information:
   - Cache hit rate (higher is better)
   - Number of cached entries
   - Average cache age
   - Number of stale entries

### Common Cache Issues

#### 1. Red Cache Indicators (Stale Data)

**Symptoms:**

- Red cache indicators (🔴) next to prices or conversion rates
- Warning messages about using stale data
- Outdated price information

**Possible Causes:**

- External API service disruption
- Network connectivity issues
- API rate limits exceeded
- System clock issues

**Diagnostic Steps:**

1. Check your internet connection
2. Visit the Status page to see if external APIs are operational
3. Check if you've made many API requests recently (rate limits)
4. Verify your system clock is accurate

#### 2. Slow Initial Load

**Symptoms:**

- First page load takes a long time
- Spinner displays for extended periods
- Console shows many API requests

**Possible Causes:**

- Empty cache (first use or after clearing)
- Many assets requiring fresh data
- Slow external API responses

**Diagnostic Steps:**

1. Check browser console for API errors
2. Monitor network tab to see which requests are slow
3. Check if this happens only on first load

#### 3. Inconsistent Data

**Symptoms:**

- Different values shown in different parts of the application
- Values change unexpectedly without refreshing
- Some assets show updated prices while others don't

**Possible Causes:**

- Partial cache updates
- Race conditions between API calls
- Different cache expiration times

**Diagnostic Steps:**

1. Check cache age for affected assets
2. Force refresh and see if the issue persists
3. Check if the issue affects specific asset types

## Resolving Cache Issues

### Basic Solutions

#### Force Refresh

The simplest solution is to force a refresh:

1. Click the refresh button (↻) in the top navigation bar
2. Wait for all data to reload
3. Verify that cache indicators show fresh data (🟢)

#### Clear Specific Cache

If issues persist with specific data types:

1. Go to Settings > Advanced
2. Click "Clear Price Cache" for price-related issues
3. Click "Clear Conversion Cache" for conversion-related issues
4. Reload the application

#### Clear All Cache

For persistent issues, clear the entire cache:

1. Go to Settings > Advanced
2. Click "Clear All Cache"
3. Confirm the action
4. Reload the application

### Advanced Solutions

#### Browser Cache Reset

If the application cache seems corrupted:

1. Open browser developer tools (F12 or Ctrl+Shift+I)
2. Right-click the refresh button and select "Empty Cache and Hard Reload"
3. Alternatively, use Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

#### Local Storage Reset

If issues persist after clearing the application cache:

1. Open browser developer tools (F12 or Ctrl+Shift+I)
2. Go to the "Application" tab
3. Select "Local Storage" in the left sidebar
4. Find and clear entries related to Cointainr
5. Reload the application

#### API Timeout Adjustment

If you experience frequent timeouts:

1. Contact your system administrator
2. Request an increase in API timeout settings
3. Consider increasing cache TTL settings

## Preventive Measures

### Optimize Asset List

Having too many assets can lead to performance issues:

1. Remove unused or duplicate assets
2. Group similar assets into categories
3. Use the batch update feature instead of individual updates

### Schedule Updates

Instead of frequent manual refreshes:

1. Use the application during off-peak hours
2. Schedule important portfolio checks after market hours
3. Use the "Update All" feature once per session

### Monitor API Usage

Keep track of your API usage:

1. Go to Settings > Advanced > API Usage
2. Check your current usage against limits
3. Consider upgrading your API plan if you consistently hit limits

## When to Contact Support

Contact your system administrator or support team if:

1. Issues persist after trying all troubleshooting steps
2. You consistently see API rate limit errors
3. Cache never seems to update even after force refresh
4. You notice significant data discrepancies
5. The application performance degrades over time

Provide the following information when reporting issues:

1. Detailed description of the problem
2. Steps to reproduce the issue
3. Screenshots showing cache indicators and error messages
4. Browser and operating system information
5. Network environment details (home, office, VPN, etc.)

## Cache Configuration Reference

For reference, these are the default cache settings:

| Data Type        | Default TTL | Environment Variable       |
| ---------------- | ----------- | -------------------------- |
| Price Data       | 15 minutes  | PRICE_CACHE_TTL_MINUTES    |
| Conversion Rates | 24 hours    | CONVERSION_CACHE_TTL_HOURS |

Your system administrator can adjust these settings to balance freshness and performance.
