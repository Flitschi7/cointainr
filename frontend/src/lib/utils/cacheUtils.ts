import type { PriceResponse, ConversionResponse, AssetCacheStatus } from '$lib/types';
import { cacheStatusService, CacheStatusType } from '$lib/services/cacheStatus';

/**
 * Utility functions for working with cache data in the frontend
 */

/**
 * Determine if a price response is using fresh or cached data
 * @param priceResponse The price response from the API
 * @returns True if the data is fresh, false if cached
 */
export function isPriceFresh(priceResponse: PriceResponse): boolean {
	// If cached flag is explicitly set to false, it's fresh
	if (priceResponse.cached === false) return true;

	// If no fetched_at timestamp, we can't determine freshness
	if (!priceResponse.fetched_at) return false;

	// Check if fetched within the last minute
	const fetchedAt = new Date(priceResponse.fetched_at).getTime();
	const now = new Date().getTime();
	return now - fetchedAt < 60000; // Less than a minute
}

/**
 * Determine if a conversion response is using fresh or cached data
 * @param conversionResponse The conversion response from the API
 * @returns True if the data is fresh, false if cached
 */
export function isConversionFresh(conversionResponse: ConversionResponse): boolean {
	// If cached flag is explicitly set to false, it's fresh
	if (conversionResponse.cached === false) return true;

	// If no fetched_at timestamp, we can't determine freshness
	if (!conversionResponse.fetched_at) return false;

	// Check if fetched within the last minute
	const fetchedAt = new Date(conversionResponse.fetched_at).getTime();
	const now = new Date().getTime();
	return now - fetchedAt < 60000; // Less than a minute
}

/**
 * Get a human-readable cache status message for an asset
 * @param cacheStatus The cache status for the asset
 * @returns A human-readable status message
 */
export function getCacheStatusMessage(cacheStatus: AssetCacheStatus | null): string {
	if (!cacheStatus || !cacheStatus.cached_at) {
		return 'No cached data available';
	}

	const statusType = cacheStatusService.getCacheStatusType(cacheStatus);
	const cacheAge = cacheStatusService.formatCacheAge(cacheStatus.cached_at);

	switch (statusType) {
		case CacheStatusType.FRESH:
			return `Fresh data fetched ${cacheAge}`;
		case CacheStatusType.VALID:
			return `Using valid cached data from ${cacheAge}`;
		case CacheStatusType.EXPIRED:
			return `Using expired cached data from ${cacheAge}`;
		default:
			return `Cache status unknown`;
	}
}

/**
 * Format cache expiration information
 * @param cacheStatus The cache status for the asset
 * @returns A string with expiration information
 */
export function getCacheExpirationInfo(cacheStatus: AssetCacheStatus | null): string {
	if (!cacheStatus || !cacheStatus.expires_at) {
		return '';
	}

	return cacheStatusService.formatTimeUntilExpiration(cacheStatus.expires_at);
}

/**
 * Get appropriate CSS classes for cache status styling
 * @param cacheStatus The cache status for the asset
 * @returns CSS class string for styling
 */
export function getCacheStatusClasses(cacheStatus: AssetCacheStatus | null): string {
	if (!cacheStatus || !cacheStatus.cached_at) {
		return 'text-gray-400';
	}

	const statusType = cacheStatusService.getCacheStatusType(cacheStatus);

	switch (statusType) {
		case CacheStatusType.FRESH:
			return 'text-emerald-500';
		case CacheStatusType.VALID:
			return 'text-blue-400';
		case CacheStatusType.EXPIRED:
			return 'text-amber-500';
		default:
			return 'text-gray-400';
	}
}

/**
 * Create a tooltip text for cache status
 * @param cacheStatus The cache status for the asset
 * @returns Tooltip text with cache information
 */
export function createCacheTooltip(cacheStatus: AssetCacheStatus | null): string {
	if (!cacheStatus || !cacheStatus.cached_at) {
		return 'No cached data available';
	}

	const statusMessage = getCacheStatusMessage(cacheStatus);
	const expirationInfo = getCacheExpirationInfo(cacheStatus);

	return expirationInfo ? `${statusMessage} • ${expirationInfo}` : statusMessage;
}
