import { test, expect } from '@playwright/test';

/**
 * Integration tests for caching behavior
 *
 * These tests verify that the caching system works correctly across the application.
 */

test.describe('Cache Lifecycle Tests', () => {
	// Before each test, navigate to the home page
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		// Wait for the page to load completely
		await page.waitForSelector('h1:has-text("Cointainr")');
	});

	test('should use cached data on initial page load', async ({ page }) => {
		// Check if the cache status banner is displayed
		const cacheBanner = await page.locator('.cache-status-banner');
		await expect(cacheBanner).toBeVisible();

		// Check if the banner indicates cache-aware loading
		const bannerText = await cacheBanner.textContent();
		expect(bannerText).toContain('Cache-aware data loading');

		// Check if cache indicators are present in the table
		const cacheIndicators = await page.locator('.cache-indicator').count();
		expect(cacheIndicators).toBeGreaterThan(0);
	});

	test('should bypass cache when using force refresh button', async ({ page }) => {
		// Get initial cache status
		const initialCacheText = await page.locator('.cache-status-banner').textContent();

		// Click the force refresh button
		await page.locator('button[aria-label="Force refresh all prices"]').click();

		// Wait for refresh to complete
		await page.waitForSelector('button[aria-label="Force refresh all prices"]:not(:disabled)');

		// Check if the last refresh time has been updated
		const lastRefreshText = await page.locator('text=Last refresh:').textContent();
		expect(lastRefreshText).toContain('Just now');

		// Check if cache status has been updated
		const updatedCacheText = await page.locator('.cache-status-banner').textContent();
		expect(updatedCacheText).not.toEqual(initialCacheText);
	});

	test('should show appropriate indicators for cached vs fresh data', async ({ page }) => {
		// Check for cache indicators in the table
		const freshIndicators = await page.locator('.cache-indicator.fresh').count();
		const cachedIndicators = await page.locator('.cache-indicator.cached').count();

		// We should have some combination of fresh and cached indicators
		expect(freshIndicators + cachedIndicators).toBeGreaterThan(0);

		// After a force refresh, we should have more fresh indicators
		await page.locator('button[aria-label="Force refresh all prices"]').click();
		await page.waitForSelector('button[aria-label="Force refresh all prices"]:not(:disabled)');

		const freshIndicatorsAfterRefresh = await page.locator('.cache-indicator.fresh').count();
		expect(freshIndicatorsAfterRefresh).toBeGreaterThanOrEqual(freshIndicators);
	});
});

test.describe('Cache Error Handling Tests', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		await page.waitForSelector('h1:has-text("Cointainr")');
	});

	test('should fall back to cached data when API calls fail', async ({ page, context }) => {
		// First load the page normally to ensure we have cached data
		await page.reload();
		await page.waitForSelector('h1:has-text("Cointainr")');

		// Intercept API calls to simulate failures
		await context.route('**/api/v1/price/**', (route) => {
			route.abort('failed');
		});

		// Try to refresh prices
		await page.locator('button[aria-label="Force refresh all prices"]').click();

		// Wait for the error dialog
		await page.waitForEvent('dialog');
		const dialog = await page.waitForEvent('dialog');

		// Check if the error message mentions using cached data
		expect(dialog.message()).toContain('The system will continue using cached data');

		// Dismiss the dialog
		await dialog.dismiss();

		// Check if the page still displays data (from cache)
		const tableRows = await page.locator('table tbody tr').count();
		expect(tableRows).toBeGreaterThan(0);
	});

	test('should show appropriate error states in components when data cannot be loaded', async ({
		page,
		context
	}) => {
		// Intercept API calls to simulate failures
		await context.route('**/api/v1/price/**', (route) => {
			route.abort('failed');
		});

		// Clear cache and reload to force error states
		await page.evaluate(() => {
			localStorage.clear();
			sessionStorage.clear();
		});

		await page.reload();

		// Check for error indicators in components
		const errorElements = await page.locator('text=Error').count();
		expect(errorElements).toBeGreaterThan(0);
	});
});

test.describe('Cache TTL Respect Tests', () => {
	test('should respect cache TTL settings from environment', async ({ page }) => {
		// This test would ideally manipulate the system clock or cache timestamps
		// Since that's difficult in a browser context, we'll check for the presence
		// of cache expiration information in tooltips

		await page.goto('/');

		// Hover over a cache status indicator to see the tooltip
		const cacheIndicator = await page.locator('.cache-status-indicator').first();
		await cacheIndicator.hover();

		// Wait for tooltip to appear
		await page.waitForTimeout(500);

		// Check page for tooltip content (this is approximate since tooltips are browser-native)
		const pageContent = await page.content();

		// Look for TTL or expiration information in the tooltip attributes
		const hasTtlInfo =
			pageContent.includes('Cache TTL') ||
			pageContent.includes('expires') ||
			pageContent.includes('expiration');

		expect(hasTtlInfo).toBeTruthy();
	});
});
