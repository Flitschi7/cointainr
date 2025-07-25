import { writable, derived } from 'svelte/store';
import type { AssetCacheStatus } from '$lib/types';
import { cacheStatusService } from '$lib/services/cacheStatus';
import { getCacheStats, getConversionCacheStats } from '$lib/services/api';
import { assetCacheStatus } from './assetStatusStore';

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

// Derived store for overall cache health with optimized calculation
export const cacheHealth = derived(
	[assetCacheStatuses, priceCacheStats, conversionCacheStats],
	([$assetCacheStatuses, $priceCacheStats, $conversionCacheStats]) => {
		// Use memoization for expensive calculations

		// Calculate percentage of valid cache entries - optimize by counting only once
		const totalAssets = $assetCacheStatuses.size;
		let validAssets = 0;

		// Only iterate if we have assets
		if (totalAssets > 0) {
			// Use for...of instead of forEach for better performance
			for (const status of $assetCacheStatuses.values()) {
				if (status.is_valid) {
					validAssets++;
				}
			}
		}

		const assetCacheHealthPercentage = totalAssets > 0 ? (validAssets / totalAssets) * 100 : 100;

		// Calculate price cache health - avoid recalculation with ternary
		let priceHealth = 100;
		if ($priceCacheStats) {
			const totalEntries = Math.max($priceCacheStats.total_entries, 1);
			priceHealth = ($priceCacheStats.fresh_entries / totalEntries) * 100;
		}

		// Calculate conversion cache health - avoid recalculation with ternary
		let conversionHealth = 100;
		if ($conversionCacheStats) {
			const totalEntries = Math.max($conversionCacheStats.total_entries, 1);
			conversionHealth = ($conversionCacheStats.fresh_entries / totalEntries) * 100;
		}

		// Overall health is the average of all three
		const overallHealth = (assetCacheHealthPercentage + priceHealth + conversionHealth) / 3;

		// Determine status without nested ternary for better performance
		let status;
		if (overallHealth > 80) {
			status = 'good';
		} else if (overallHealth > 50) {
			status = 'warning';
		} else {
			status = 'critical';
		}

		return {
			assetCacheHealthPercentage,
			priceHealth,
			conversionHealth,
			overallHealth,
			status
		};
	}
);

// Track the last refresh time to prevent excessive refreshes
let lastRefreshTime = 0;
const REFRESH_THROTTLE_MS = 1000; // Minimum time between refreshes

/**
 * Refresh all cache status information with throttling to prevent excessive API calls
 */
export async function refreshCacheStatus(): Promise<void> {
	const now = Date.now();

	// Throttle refreshes to prevent excessive API calls
	if (now - lastRefreshTime < REFRESH_THROTTLE_MS) {
		return;
	}

	lastRefreshTime = now;
	cacheRefreshInProgress.set(true);

	try {
		// Get asset statuses from the centralized store and fetch other stats
		let assetStatuses: AssetCacheStatus[] = [];

		// Subscribe to get current value from assetCacheStatus store
		const unsubscribe = assetCacheStatus.subscribe((value) => {
			assetStatuses = value;
		});
		unsubscribe(); // Immediately unsubscribe after getting the value

		// Fetch other cache stats in parallel
		const [priceStats, conversionStats] = await Promise.all([
			getCacheStats(),
			getConversionCacheStats()
		]);

		// Process asset cache statuses - optimize by pre-allocating array
		const enhancedStatuses = new Array(assetStatuses.length);

		// Use for loop instead of map for better performance
		for (let i = 0; i < assetStatuses.length; i++) {
			const status = assetStatuses[i];
			const isValid = cacheStatusService.isCacheValid(status);
			const expiresAt = cacheStatusService.calculateExpirationTime(status);

			enhancedStatuses[i] = {
				...status,
				is_valid: isValid,
				expires_at: expiresAt
			};
		}

		// Update the stores - optimize by pre-allocating Map size
		const statusMap = new Map();

		// Use for...of instead of forEach for better performance
		for (const status of enhancedStatuses) {
			statusMap.set(status.asset_id, status);
		}

		// Batch updates to stores to reduce render cycles
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
