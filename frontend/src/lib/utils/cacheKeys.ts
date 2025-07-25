/**
 * Utility functions for generating consistent cache keys
 */

/**
 * Generate a cache key for price data
 * @param type Asset type (crypto, stock)
 * @param symbol Asset symbol
 * @returns Cache key string
 */
export function getPriceCacheKey(type: string, symbol: string): string {
	return `price:${type}:${symbol.toLowerCase()}`;
}

/**
 * Generate a cache key for conversion rate
 * @param fromCurrency Source currency code
 * @param toCurrency Target currency code
 * @returns Cache key string
 */
export function getConversionCacheKey(fromCurrency: string, toCurrency: string): string {
	return `conversion:${fromCurrency.toUpperCase()}:${toCurrency.toUpperCase()}`;
}

/**
 * Generate a cache key for asset data
 * @param assetId Asset ID
 * @returns Cache key string
 */
export function getAssetCacheKey(assetId: number): string {
	return `asset:${assetId}`;
}

/**
 * Generate a cache key for portfolio data
 * @param currency Target currency
 * @returns Cache key string
 */
export function getPortfolioCacheKey(currency: string): string {
	return `portfolio:${currency.toUpperCase()}`;
}

/**
 * Generate a cache key for batch price data
 * @param symbols Array of asset symbols
 * @param types Array of asset types
 * @returns Cache key string
 */
export function getBatchPriceCacheKey(symbols: string[], types: string[]): string {
	// Sort to ensure consistent key regardless of array order
	const sortedSymbols = [...symbols].sort();
	const sortedTypes = [...types].sort();

	return `batch:prices:${sortedSymbols.join(',')}:${sortedTypes.join(',')}`;
}
