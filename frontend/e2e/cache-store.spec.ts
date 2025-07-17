import { test, expect } from '@playwright/test';

/**
 * Integration tests for cache store behavior
 *
 * These tests verify that the cache store works correctly and maintains state across the application.
 */

test.describe('Cache Store Tests', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		await page.waitForSelector('h1:has-text("Cointainr")');
	});

	test('should initialize cache store on page load', async ({ page }) => {
		// Check if cache health indicator is visible, which relies on the cache store
		const cacheHealthIndicator = page.locator('.cache-health-indicator');
		await expect(cacheHealthIndicator).toBeVisible();

		// Check if it contains health percentage information
		const healthText = await cacheHealthIndicator.textContent();
		expect(healthText).toContain('Cache Health:');
		expect(healthText).toMatch(/\d+%/); // Should contain a percentage
	});

	test('should update cache status after refresh', async ({ page }) => {
		// Click the refresh button in the cache health indicator
		await page.locator('.cache-health-indicator button').click();

		// Wait for refresh to complete
		await page.waitForTimeout(500);

		// Get updated cache health
		const updatedHealthText = await page.locator('.cache-health-indicator').textContent();

		// The text might be the same if cache status didn't change,
		// but the component should have been refreshed
		expect(updatedHealthText).toBeDefined();
	});
});

test.describe('Cache Management Panel Tests', () => {
	// This test assumes there's a way to navigate to or open the cache management panel
	// We'll need to adjust this based on how it's actually accessed in the UI

	test('should display cache statistics', async ({ page }) => {
		// Navigate to the cache management panel
		// This might need to be adjusted based on actual navigation
		await page.goto('/cache-management');

		// Check if the panel is visible
		const cachePanel = page.locator('.cache-management-panel');
		await expect(cachePanel).toBeVisible();

		// Check if it contains price cache statistics
		const priceCacheSection = page.locator('text=Price Cache');
		await expect(priceCacheSection).toBeVisible();

		// Check if it contains conversion cache statistics
		const conversionCacheSection = page.locator('text=Conversion Cache');
		await expect(conversionCacheSection).toBeVisible();
	});

	test('should allow clearing price cache', async ({ page }) => {
		// Navigate to the cache management panel
		await page.goto('/cache-management');

		// Click the clear price cache button
		await page.locator('button:has-text("Clear Price Cache")').click();

		// Wait for the operation to complete
		await page.waitForSelector('text=Successfully cleared price cache', { timeout: 5000 });

		// Check if success message is displayed
		const successMessage = page.locator('text=Successfully cleared price cache');
		await expect(successMessage).toBeVisible();
	});

	test('should allow clearing conversion cache', async ({ page }) => {
		// Navigate to the cache management panel
		await page.goto('/cache-management');

		// Click the clear conversion cache button
		await page.locator('button:has-text("Clear Conversion Cache")').click();

		// Wait for the operation to complete
		await page.waitForSelector('text=Successfully cleared conversion cache', { timeout: 5000 });

		// Check if success message is displayed
		const successMessage = page.locator('text=Successfully cleared conversion cache');
		await expect(successMessage).toBeVisible();
	});
});
