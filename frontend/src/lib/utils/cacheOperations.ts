import { getStockPrice, getCryptoPrice, getConversionRate } from '$lib/services/api';
import type { Asset } from '$lib/types';
import { assetCacheStatus } from '$lib/stores/assetStatusStore';

/**
 * Utility functions for cache-related operations
 */

/**
 * Get the current price for an asset with cache awareness
 * @param asset The asset to get price for
 * @param forceRefresh Whether to force refresh the price
 * @returns The price and cache information
 */
export async function getAssetPrice(
	asset: Asset,
	forceRefresh: boolean = false
): Promise<{
	price: number;
	currency: string;
	cached: boolean;
	fetched_at: string;
	source: string;
	cache_valid_until?: string;
}> {
	if (asset.type === 'cash') {
		// Cash assets always have a price of 1 in their own currency
		return {
			price: 1,
			currency: asset.currency || 'USD',
			cached: false,
			fetched_at: new Date().toISOString(),
			source: 'system'
		};
	}

	try {
		let priceData;

		if (asset.type === 'stock') {
			priceData = await getStockPrice(asset.symbol || '', forceRefresh);
		} else if (asset.type === 'crypto') {
			priceData = await getCryptoPrice(asset.symbol || '', forceRefresh);
		} else {
			throw new Error(`Unsupported asset type: ${asset.type}`);
		}

		// Note: Cache status will be automatically refreshed by CacheStatusProvider

		// Ensure all required properties are present and have the correct types
		return {
			...priceData,
			cached: priceData.cached === true,
			fetched_at: priceData.fetched_at || new Date().toISOString(),
			source: priceData.source || (priceData.cached ? 'cache' : 'api')
		};
	} catch (error) {
		console.error(`Failed to fetch price for ${asset.symbol}:`, error);
		throw error;
	}
}

/**
 * Get prices for multiple assets with cache awareness
 * @param assets The assets to get prices for
 * @param forceRefresh Whether to force refresh all prices
 * @returns Map of asset IDs to price information
 */
export async function getMultipleAssetPrices(
	assets: Asset[],
	forceRefresh: boolean = false
): Promise<
	Map<
		number,
		{
			price: number;
			currency: string;
			cached: boolean;
			fetched_at: string;
			source: string;
			cache_valid_until?: string;
		}
	>
> {
	// First check which assets have valid cache to optimize API calls
	const assetCacheStatuses = await Promise.all(
		assets.map(async (asset) => {
			try {
				const isValid = await isAssetCacheValid(asset.id);
				return {
					asset,
					hasValidCache: isValid
				};
			} catch (error) {
				console.error(`Failed to check cache validity for ${asset.symbol}:`, error);
				return {
					asset,
					hasValidCache: false
				};
			}
		})
	);

	// Group assets by cache status to optimize API calls
	const assetsWithValidCache = assetCacheStatuses
		.filter((status) => status.hasValidCache)
		.map((status) => status.asset);

	const assetsNeedingRefresh = assetCacheStatuses
		.filter((status) => !status.hasValidCache)
		.map((status) => status.asset);

	// Log cache efficiency information
	console.log(
		`Cache efficiency: ${assetsWithValidCache.length}/${assets.length} assets have valid cache (${
			assets.length > 0 ? Math.round((assetsWithValidCache.length / assets.length) * 100) : 0
		}%)`
	);

	// Process all assets in parallel
	const pricePromises = assets.map(async (asset) => {
		try {
			// Only force refresh if explicitly requested
			// On page load (forceRefresh = false), always use cached data even if stale
			const priceData = await getAssetPrice(asset, forceRefresh);
			return {
				assetId: asset.id,
				priceData
			};
		} catch (error) {
			console.error(`Failed to fetch price for ${asset.symbol}:`, error);
			return {
				assetId: asset.id,
				priceData: {
					price: 0,
					currency: 'USD',
					cached: false,
					fetched_at: new Date().toISOString(),
					source: 'error'
				}
			};
		}
	});

	const prices = await Promise.all(pricePromises);

	// Create a map of asset ID to price data
	const priceMap = new Map();
	prices.forEach(({ assetId, priceData }) => {
		priceMap.set(assetId, priceData);
	});

	return priceMap;
}

/**
 * Check if cache is valid for an asset
 * @param assetId The asset ID to check
 * @returns True if cache is valid, false otherwise
 */
export async function isAssetCacheValid(assetId: number): Promise<boolean> {
	try {
		// Get current cache status from the centralized store
		let currentStatuses: any[] = [];
		const unsubscribe = assetCacheStatus.subscribe((value) => {
			currentStatuses = value;
		});
		unsubscribe();

		const cacheStatus = currentStatuses.find((status) => status.asset_id === assetId);
		return cacheStatus?.is_valid || false;
	} catch (error) {
		console.error(`Failed to check cache validity for asset ${assetId}:`, error);
		return false;
	}
}

/**
 * Get conversion rate with cache awareness
 * @param fromCurrency The source currency
 * @param toCurrency The target currency
 * @param forceRefresh Whether to force refresh the rate
 * @returns The conversion rate and cache information
 */
export async function getCachedConversionRate(
	fromCurrency: string,
	toCurrency: string,
	forceRefresh: boolean = false
) {
	try {
		const rateData = await getConversionRate(fromCurrency, toCurrency, forceRefresh);

		// Note: Cache status will be automatically refreshed by CacheStatusProvider

		// Ensure all required properties are present and have the correct types
		return {
			...rateData,
			cached: rateData.cached === true,
			fetched_at: rateData.fetched_at || new Date().toISOString(),
			source: rateData.source || (rateData.cached ? 'cache' : 'api')
		};
	} catch (error) {
		console.error(`Failed to fetch conversion rate from ${fromCurrency} to ${toCurrency}:`, error);
		throw error;
	}
}
