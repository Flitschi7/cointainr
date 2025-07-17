import { writable, derived } from 'svelte/store';
import type { AssetCacheStatus } from '$lib/services/cacheStatus';
import { cacheStatusService } from '$lib/services/cacheStatus';
import { getAssetCacheStatus, getCacheStats, getConversionCacheStats } from '$lib/services/api';

// Store for all asset cache statuses
export const assetCacheStatuses = writable<Map<number, AssetCacheStatus>>(new Map());

// Store for price cache statistics
export const priceCacheStats = writable<{
	total_entries: number;
	fresh_entries: number;
	stock_entries: number;
	crypto_entries: number;
	cache_age_minutes: number;
} | null>(null);

// Store for conversion cache statistics
export const conversionCacheStats = writable<{
	total_entries: number;
	fresh_entries: number;
	cache_age_hours: number;
} | null>(null);

// Store for last refresh time
export const lastCacheRefresh = writable<Date | null>(null);

// Store for cache refresh in progress
export const cacheRefreshInProgress = writable<boolean>(false);

// Derived store for overall cache health
export const cacheHealth = derived(
	[assetCacheStatuses, priceCacheStats, conversionCacheStats],
	([$assetCacheStatuses, $priceCacheStats, $conversionCacheStats]) => {
		// Calculate percentage of valid cache entries
		const totalAssets = $assetCacheStatuses.size;
		let validAssets = 0;

		$assetCacheStatuses.forEach((status) => {
			if (status.is_valid) {
				validAssets++;
			}
		});

		const assetCacheHealthPercentage = totalAssets > 0 ? (validAssets / totalAssets) * 100 : 100;

		// Calculate price cache health
		const priceHealth = $priceCacheStats
			? ($priceCacheStats.fresh_entries / Math.max($priceCacheStats.total_entries, 1)) * 100
			: 100;

		// Calculate conversion cache health
		const conversionHealth = $conversionCacheStats
			? ($conversionCacheStats.fresh_entries / Math.max($conversionCacheStats.total_entries, 1)) *
				100
			: 100;

		// Overall health is the average of all three
		const overallHealth = (assetCacheHealthPercentage + priceHealth + conversionHealth) / 3;

		return {
			assetCacheHealthPercentage,
			priceHealth,
			conversionHealth,
			overallHealth,
			status: overallHealth > 80 ? 'good' : overallHealth > 50 ? 'warning' : 'critical'
		};
	}
);

/**
 * Refresh all cache status information
 */
export async function refreshCacheStatus(): Promise<void> {
	cacheRefreshInProgress.set(true);

	try {
		// Fetch all cache statuses in parallel
		const [assetStatuses, priceStats, conversionStats] = await Promise.all([
			getAssetCacheStatus(),
			getCacheStats(),
			getConversionCacheStats()
		]);

		// Process asset cache statuses
		const enhancedStatuses = assetStatuses.map((status) => {
			const isValid = cacheStatusService.isCacheValid(status);
			const expiresAt = cacheStatusService.calculateExpirationTime(status);

			return {
				...status,
				is_valid: isValid,
				expires_at: expiresAt
			};
		});

		// Update the stores
		const statusMap = new Map();
		enhancedStatuses.forEach((status) => {
			statusMap.set(status.asset_id, status);
		});

		assetCacheStatuses.set(statusMap);
		priceCacheStats.set(priceStats);
		conversionCacheStats.set(conversionStats);
		lastCacheRefresh.set(new Date());
	} catch (error) {
		console.error('Failed to refresh cache status:', error);
	} finally {
		cacheRefreshInProgress.set(false);
	}
}

/**
 * Get cache status for a specific asset
 * @param assetId The asset ID to get cache status for
 * @returns The cache status for the asset or null if not found
 */
export function getAssetCacheStatusFromStore(assetId: number): AssetCacheStatus | null {
	let result: AssetCacheStatus | null = null;

	assetCacheStatuses.subscribe((statuses) => {
		result = statuses.get(assetId) || null;
	})();

	return result;
}

// Initialize the cache status on app start
export function initializeCacheStatus(): void {
	refreshCacheStatus();
}
