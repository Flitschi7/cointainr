/**
 * Enhanced API service with retry logic and improved error handling
 *
 * This service wraps the original API functions with retry logic and
 * standardized error handling to improve resilience and user experience.
 */

import * as enhancedApi from './enhancedApi';
import { createRetryableFunction } from '$lib/utils/retryUtils';
import type { RetryOptions } from '$lib/utils/retryUtils';
import type {
	Asset,
	PriceResponse,
	ConversionResponse,
	ConversionRateResponse,
	CacheStats,
	RefreshAllResponse,
	AssetCacheStatus
} from '$lib/types';

// Default retry options for API calls
const defaultApiRetryOptions: RetryOptions = {
	maxRetries: 2,
	initialDelay: 1000,
	maxDelay: 10000,
	backoffFactor: 2,
	isRetryable: (error: any) => {
		// Retry network errors and server errors
		if (error instanceof TypeError && error.message.includes('network')) {
			return true;
		}

		// Retry server errors (5xx)
		if (error.status && error.status >= 500 && error.status < 600) {
			return true;
		}

		// Retry rate limit errors (429)
		if (error.status && error.status === 429) {
			return true;
		}

		// Don't retry other client errors (4xx)
		return false;
	},
	onRetry: (attempt, delay, error) => {
		console.warn(`API retry attempt ${attempt} after ${delay}ms due to error:`, error);
	}
};

// Enhanced error handling is now handled by the enhancedApi module

// Create retryable versions of API functions

/**
 * Get assets with retry logic and performance tracking
 */
export const getAssets = createRetryableFunction(
	async (options?: enhancedApi.ApiOptions): Promise<Asset[]> => {
		try {
			// Track API call with performance monitoring
			const performanceMonitoring = await import('./performanceMonitoring');
			return await performanceMonitoring.withPerformanceTracking(
				'GET /api/v1/assets',
				async () => await enhancedApi.getAssets(options)
			);
		} catch (error) {
			console.error('Failed to fetch assets:', error);
			throw enhanceError(error, 'Failed to fetch assets');
		}
	},
	defaultApiRetryOptions
);

/**
 * Get price with retry logic and performance tracking
 */
export const getPrice = createRetryableFunction(
	async (
		symbol: string,
		type: 'crypto' | 'stock' | 'derivative',
		options?: enhancedApi.ApiOptions
	): Promise<PriceResponse> => {
		try {
			// Track API call with performance monitoring
			const performanceMonitoring = await import('./performanceMonitoring');
			return await performanceMonitoring.withPerformanceTracking(
				`GET /api/v1/price/${type}/${symbol}`,
				async () => await enhancedApi.getPrice(symbol, type, options)
			);
		} catch (error) {
			console.error(`Failed to fetch ${type} price for ${symbol}:`, error);
			throw enhanceError(error, `Failed to fetch ${type} price for ${symbol}`);
		}
	},
	defaultApiRetryOptions
);

/**
 * Convert currency with retry logic and performance tracking
 */
export const convertCurrency = createRetryableFunction(
	async (
		fromCurrency: string,
		toCurrency: string,
		amount: number,
		options?: enhancedApi.ApiOptions
	): Promise<ConversionResponse> => {
		try {
			// Track API call with performance monitoring
			const performanceMonitoring = await import('./performanceMonitoring');
			return await performanceMonitoring.withPerformanceTracking(
				`GET /api/v1/conversion/convert`,
				async () => await enhancedApi.convertCurrency(fromCurrency, toCurrency, amount, options)
			);
		} catch (error) {
			console.error(`Failed to convert ${amount} ${fromCurrency} to ${toCurrency}:`, error);
			throw enhanceError(error, `Failed to convert ${fromCurrency} to ${toCurrency}`);
		}
	},
	defaultApiRetryOptions
);

/**
 * Get conversion rate with retry logic
 */
export const getConversionRate = createRetryableFunction(
	async (
		fromCurrency: string,
		toCurrency: string,
		options?: enhancedApi.ApiOptions
	): Promise<ConversionRateResponse> => {
		try {
			return await enhancedApi.getConversionRate(fromCurrency, toCurrency, options);
		} catch (error) {
			console.error(`Failed to get conversion rate from ${fromCurrency} to ${toCurrency}:`, error);
			throw enhanceError(
				error,
				`Failed to get conversion rate from ${fromCurrency} to ${toCurrency}`
			);
		}
	},
	defaultApiRetryOptions
);

/**
 * Batch get prices with retry logic
 */
export const batchGetPrices = createRetryableFunction(
	async (
		symbols: string[],
		types: ('crypto' | 'stock' | 'derivative')[],
		options?: enhancedApi.ApiOptions
	): Promise<PriceResponse[]> => {
		try {
			return await enhancedApi.batchGetPrices(symbols, types, options);
		} catch (error) {
			console.error('Failed to batch fetch prices:', error);
			throw enhanceError(error, 'Failed to batch fetch prices');
		}
	},
	defaultApiRetryOptions
);

/**
 * Batch convert currency with retry logic
 */
export const batchConvertCurrency = createRetryableFunction(
	async (
		amounts: number[],
		fromCurrencies: string[],
		toCurrencies: string[],
		options?: enhancedApi.ApiOptions
	): Promise<ConversionResponse[]> => {
		try {
			return await enhancedApi.batchConvertCurrency(amounts, fromCurrencies, toCurrencies, options);
		} catch (error) {
			console.error('Failed to batch convert currencies:', error);
			throw enhanceError(error, 'Failed to batch convert currencies');
		}
	},
	defaultApiRetryOptions
);

/**
 * Refresh all prices with retry logic
 */
export const refreshAllPrices = createRetryableFunction(async (): Promise<RefreshAllResponse> => {
	try {
		return await enhancedApi.refreshAllPrices();
	} catch (error) {
		console.error('Failed to refresh all prices:', error);
		throw enhanceError(error, 'Failed to refresh all prices');
	}
}, defaultApiRetryOptions);

/**
 * Clear price cache with retry logic
 */
export const clearPriceCache = createRetryableFunction(async (): Promise<{ message: string }> => {
	try {
		return await enhancedApi.clearPriceCache();
	} catch (error) {
		console.error('Failed to clear price cache:', error);
		throw enhanceError(error, 'Failed to clear price cache');
	}
}, defaultApiRetryOptions);

/**
 * Clear conversion cache with retry logic
 */
export const clearConversionCache = createRetryableFunction(
	async (): Promise<{ message: string }> => {
		try {
			return await enhancedApi.clearConversionCache();
		} catch (error) {
			console.error('Failed to clear conversion cache:', error);
			throw enhanceError(error, 'Failed to clear conversion cache');
		}
	},
	defaultApiRetryOptions
);

/**
 * Get cache stats with retry logic
 */
export const getCacheStats = createRetryableFunction(async (): Promise<CacheStats> => {
	try {
		return await enhancedApi.getCacheStats();
	} catch (error) {
		console.error('Failed to get cache stats:', error);
		throw enhanceError(error, 'Failed to get cache statistics');
	}
}, defaultApiRetryOptions);

/**
 * Get asset cache status with retry logic
 */
export const getAssetCacheStatus = createRetryableFunction(
	async (): Promise<AssetCacheStatus[]> => {
		try {
			return await enhancedApi.getAssetCacheStatus();
		} catch (error) {
			console.error('Failed to get asset cache status:', error);
			throw enhanceError(error, 'Failed to get asset cache status');
		}
	},
	defaultApiRetryOptions
);

/**
 * Enhance error object with additional information
 * @param error Original error
 * @param friendlyMessage User-friendly error message
 * @returns Enhanced error object
 */
function enhanceError(error: any, friendlyMessage: string): Error {
	// Create a new error with the friendly message
	const enhancedError: any = new Error(friendlyMessage);

	// Copy properties from the original error
	if (error instanceof Error) {
		enhancedError.originalMessage = error.message;
		enhancedError.stack = error.stack;
		enhancedError.name = error.name;
	}

	// Add additional context
	enhancedError.timestamp = new Date().toISOString();
	enhancedError.originalError = error;

	// Add network-specific information
	if (error instanceof TypeError && error.message.includes('network')) {
		enhancedError.isNetworkError = true;
	}

	// Add API-specific information
	if (error.status) {
		enhancedError.status = error.status;
		enhancedError.statusText = error.statusText;
		enhancedError.data = error.data;

		// Categorize the error
		if (error.status >= 500) {
			enhancedError.category = 'server';
		} else if (error.status === 429) {
			enhancedError.category = 'rate-limit';
		} else if (error.status >= 400) {
			enhancedError.category = 'client';
		}
	}

	return enhancedError;
}
