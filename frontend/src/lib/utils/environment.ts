/**
 * Environment configuration utility
 *
 * This module provides access to environment variables and configuration settings
 * with appropriate defaults.
 */

/**
 * Get the price cache TTL in milliseconds
 * @returns TTL in milliseconds
 */
export function getPriceCacheTTL(): number {
	// Default to 15 minutes if not specified
	const defaultTTL = 15 * 60 * 1000; // 15 minutes in milliseconds

	// Try to get from environment
	const envTTL = import.meta.env.VITE_PRICE_CACHE_TTL_MINUTES;
	if (envTTL && !isNaN(Number(envTTL))) {
		return Number(envTTL) * 60 * 1000; // Convert minutes to milliseconds
	}

	return defaultTTL;
}

/**
 * Get the conversion cache TTL in milliseconds
 * @returns TTL in milliseconds
 */
export function getConversionCacheTTL(): number {
	// Default to 24 hours if not specified
	const defaultTTL = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

	// Try to get from environment
	const envTTL = import.meta.env.VITE_CONVERSION_CACHE_TTL_HOURS;
	if (envTTL && !isNaN(Number(envTTL))) {
		return Number(envTTL) * 60 * 60 * 1000; // Convert hours to milliseconds
	}

	return defaultTTL;
}

/**
 * Get the default currency
 * @returns Default currency code
 */
export function getDefaultCurrency(): string {
	// Default to USD if not specified
	return import.meta.env.VITE_DEFAULT_CURRENCY || 'USD';
}

/**
 * Check if force refresh only mode is enabled
 * @returns True if force refresh only mode is enabled
 */
export function isForceRefreshOnlyMode(): boolean {
	const forceRefreshOnly = import.meta.env.VITE_FORCE_REFRESH_ONLY;
	return forceRefreshOnly === 'true' || forceRefreshOnly === '1' || forceRefreshOnly === 'yes';
}

/**
 * Get the API base URL
 * @returns API base URL
 */
export function getApiBaseUrl(): string {
	return import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
}

/**
 * Get all environment configuration settings
 * @returns Object containing all environment settings
 */
export function getAllEnvironmentSettings(): Record<string, any> {
	return {
		priceCacheTTL: {
			value: getPriceCacheTTL(),
			displayValue: `${getPriceCacheTTL() / (60 * 1000)} minutes`,
			envVariable: 'VITE_PRICE_CACHE_TTL_MINUTES'
		},
		conversionCacheTTL: {
			value: getConversionCacheTTL(),
			displayValue: `${getConversionCacheTTL() / (60 * 60 * 1000)} hours`,
			envVariable: 'VITE_CONVERSION_CACHE_TTL_HOURS'
		},
		defaultCurrency: {
			value: getDefaultCurrency(),
			displayValue: getDefaultCurrency(),
			envVariable: 'VITE_DEFAULT_CURRENCY'
		},
		forceRefreshOnly: {
			value: isForceRefreshOnlyMode(),
			displayValue: isForceRefreshOnlyMode() ? 'Enabled' : 'Disabled',
			envVariable: 'VITE_FORCE_REFRESH_ONLY'
		},
		apiBaseUrl: {
			value: getApiBaseUrl(),
			displayValue: getApiBaseUrl(),
			envVariable: 'VITE_API_BASE_URL'
		}
	};
}
