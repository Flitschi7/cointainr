import {
	getAssets,
	getAssetCacheStatus,
	getCacheStats,
	getConversionCacheStats
} from '$lib/services/api';
// Note: Cache management is now handled by CacheStatusProvider
import { cacheStatusService } from '$lib/services/cacheStatus';
import { getMultipleAssetPrices } from '$lib/utils/cacheOperations';
import { devLog } from '$lib/utils/logger';

/** @type {import('./$types').PageLoad} */
export async function load() {
	try {
		// Load assets, cache status, and cache statistics in parallel
		// Note: We're not forcing refresh here, so we'll use cached data if valid
		const [assets, cacheStatusData, cacheStats, conversionStats] = await Promise.all([
			getAssets(),
			getAssetCacheStatus(),
			getCacheStats(),
			getConversionCacheStats()
		]);

		// Process cache status to add validity information
		const enhancedCacheStatus = cacheStatusData.map((status) => {
			const isValid = cacheStatusService.isCacheValid(status);
			const expiresAt = cacheStatusService.calculateExpirationTime(status);

			return {
				...status,
				is_valid: isValid,
				expires_at: expiresAt
			};
		});

		// Note: Cache initialization is now handled by CacheStatusProvider
		// No need to initialize the old cache store here

		// Only load prices for non-cash assets to avoid unnecessary API calls
		const pricedAssets = assets.filter((asset) => asset.type !== 'cash');
		let initialPrices = null;
		let cacheHitCount = 0;
		let apiCallCount = 0;

		if (pricedAssets.length > 0) {
			try {
				// Check which assets have valid cache before making API calls
				const cacheValidityChecks = pricedAssets.map((asset) => {
					const cacheStatus = enhancedCacheStatus.find((status) => status.asset_id === asset.id);
					return {
						asset,
						hasValidCache: cacheStatus?.is_valid || false
					};
				});

				// Count how many assets have valid cache vs. need API calls
				cacheHitCount = cacheValidityChecks.filter((check) => check.hasValidCache).length;
				apiCallCount = cacheValidityChecks.filter((check) => !check.hasValidCache).length;

				// Only load prices if we have assets that need them
				// On page load, NEVER force refresh - only use cached data from database
				// Even if cache is stale, we use it. Only "Force Refresh" button should call external APIs
				initialPrices = await getMultipleAssetPrices(pricedAssets, false);

				devLog.info(
					`Page load completed: ${initialPrices.size} prices loaded (${cacheHitCount} from cache, ${apiCallCount} from API)`
				);
			} catch (error) {
				console.error('Failed to pre-load asset prices:', error);
				// Even if we fail to load prices, we should continue with the page load
				// The individual components will handle fallback behavior
			}
		}

		return {
			assets,
			cacheStatus: enhancedCacheStatus,
			// Enhanced cache metadata with detailed information
			cacheMetadata: {
				loadedAt: new Date().toISOString(),
				usedCache: true, // We always respect cache during page load
				initialPricesLoaded: initialPrices ? initialPrices.size : 0,
				totalAssets: assets.length,
				pricedAssets: pricedAssets.length,
				cacheHits: cacheHitCount,
				apiCalls: apiCallCount,
				cacheEfficiency: pricedAssets.length > 0 ? (cacheHitCount / pricedAssets.length) * 100 : 0,
				// Include cache statistics for better monitoring
				priceCache: cacheStats,
				conversionCache: conversionStats
			},
			// Include initial prices in the page data to avoid duplicate API calls
			initialPrices: initialPrices ? Object.fromEntries(initialPrices) : null
		};
	} catch (error) {
		console.error('Failed to load page data:', error);
		// Handle error properly with type checking
		const errorMessage = error instanceof Error ? error.message : String(error);
		return {
			assets: [],
			cacheStatus: [],
			initialPrices: null,
			cacheMetadata: {
				loadedAt: new Date().toISOString(),
				usedCache: false,
				initialPricesLoaded: 0,
				totalAssets: 0,
				pricedAssets: 0,
				cacheHits: 0,
				apiCalls: 0,
				cacheEfficiency: 0,
				error: errorMessage
			}
		};
	}
}
