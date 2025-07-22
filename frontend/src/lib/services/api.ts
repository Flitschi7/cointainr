import type {
	Asset,
	PriceResponse,
	ConversionResponse,
	ConversionRateResponse,
	CacheStats,
	RefreshAllResponse,
	AssetCacheStatus
} from '$lib/types';

// Environment-aware API base URL configuration
// In Docker/production: Use relative URLs for same-origin requests
// In development: Use environment variable or fallback to dev server
function getApiBaseUrl(): string {
	// Check if we're in a browser environment
	if (typeof window !== 'undefined') {
		// In production/Docker, use relative URL for same-origin requests
		// This works when frontend and backend are served from the same origin
		if (
			window.location.origin.includes('localhost:8893') ||
			window.location.origin.includes('127.0.0.1:8893') ||
			import.meta.env.PROD
		) {
			return '/api/v1';
		}
	}

	// In development, use environment variable or default dev server
	return import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
}

const API_BASE_URL = getApiBaseUrl();

// Debug logging for development
if (import.meta.env.DEV) {
	console.log(`[API] Using API base URL: ${API_BASE_URL}`);
	console.log(`[API] Environment:`, {
		origin: typeof window !== 'undefined' ? window.location.origin : 'SSR',
		VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
		PROD: import.meta.env.PROD,
		DEV: import.meta.env.DEV
	});
}

// --- Asset API Service ---

/**
 * Fetch all assets from the backend API.
 */
export async function getAssets(): Promise<Asset[]> {
	const response = await fetch(`${API_BASE_URL}/assets/`);
	if (!response.ok) {
		throw new Error('Failed to fetch assets');
	}
	return await response.json();
}

/**
 * Create a new asset.
 */
export async function createAsset(assetData: Omit<Asset, 'id'>): Promise<Asset> {
	const response = await fetch(`${API_BASE_URL}/assets/`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(assetData)
	});
	if (!response.ok) {
		throw new Error('Failed to create asset');
	}
	return await response.json();
}

/**
 * Delete an asset by ID.
 */
export async function deleteAsset(assetId: number): Promise<void> {
	const response = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error('Failed to delete asset');
	}
}

/**
 * Update an asset by ID.
 */
export async function updateAsset(
	assetId: number,
	assetData: Partial<Omit<Asset, 'id'>>
): Promise<Asset> {
	const response = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(assetData)
	});
	if (!response.ok) {
		throw new Error('Failed to update asset');
	}
	return await response.json();
}

/**
 * Get stock price with caching support.
 */
export async function getStockPrice(
	symbol: string,
	forceRefresh: boolean = false
): Promise<PriceResponse> {
	const url = new URL(`${API_BASE_URL}/price/stock/${symbol}`);
	if (forceRefresh) {
		url.searchParams.set('force_refresh', 'true');
	}

	const response = await fetch(url.toString());
	if (!response.ok) {
		throw new Error('Failed to fetch stock price');
	}
	return await response.json();
}

/**
 * Get cryptocurrency price with caching support.
 */
export async function getCryptoPrice(
	symbol: string,
	forceRefresh: boolean = false
): Promise<PriceResponse> {
	const url = new URL(`${API_BASE_URL}/price/crypto/${symbol}`);
	if (forceRefresh) {
		url.searchParams.set('force_refresh', 'true');
	}

	const response = await fetch(url.toString());
	if (!response.ok) {
		throw new Error('Failed to fetch crypto price');
	}
	return await response.json();
}

/**
 * Convert currency amount with caching support.
 */
export async function convertCurrency(
	fromCurrency: string,
	toCurrency: string,
	amount: number,
	forceRefresh: boolean = false
): Promise<ConversionResponse> {
	const url = new URL(`${API_BASE_URL}/price/convert`);
	url.searchParams.set('from_currency', fromCurrency);
	url.searchParams.set('to_currency', toCurrency);
	url.searchParams.set('amount', amount.toString());
	if (forceRefresh) {
		url.searchParams.set('force_refresh', 'true');
	}

	const response = await fetch(url.toString());
	if (!response.ok) {
		throw new Error('Failed to convert currency');
	}
	return await response.json();
}

/**
 * Get conversion rate between two currencies with caching support.
 */
export async function getConversionRate(
	fromCurrency: string,
	toCurrency: string,
	forceRefresh: boolean = false
): Promise<ConversionRateResponse> {
	const url = new URL(`${API_BASE_URL}/price/rate/${fromCurrency}/${toCurrency}`);
	if (forceRefresh) {
		url.searchParams.set('force_refresh', 'true');
	}

	const response = await fetch(url.toString());
	if (!response.ok) {
		throw new Error('Failed to fetch conversion rate');
	}
	return await response.json();
}

/**
 * Refresh all asset prices (force fresh API calls).
 */
export async function refreshAllPrices(): Promise<RefreshAllResponse> {
	const response = await fetch(`${API_BASE_URL}/price/refresh-all`, {
		method: 'POST'
	});
	if (!response.ok) {
		throw new Error('Failed to refresh all prices');
	}
	return await response.json();
}

/**
 * Clear the price cache.
 */
export async function clearPriceCache(): Promise<{ message: string }> {
	const response = await fetch(`${API_BASE_URL}/price/cache`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error('Failed to clear price cache');
	}
	return await response.json();
}

/**
 * Get price cache statistics.
 */
export async function getCacheStats(): Promise<CacheStats> {
	const response = await fetch(`${API_BASE_URL}/price/cache/stats`);
	if (!response.ok) {
		throw new Error('Failed to fetch cache stats');
	}
	return await response.json();
}

/**
 * Clear the conversion cache.
 */
export async function clearConversionCache(): Promise<{ message: string }> {
	const response = await fetch(`${API_BASE_URL}/price/cache/conversions`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error('Failed to clear conversion cache');
	}
	return await response.json();
}

/**
 * Get conversion cache statistics.
 */
export async function getConversionCacheStats(): Promise<{
	total_entries: number;
	fresh_entries: number;
	cache_age_hours: number;
}> {
	const response = await fetch(`${API_BASE_URL}/price/cache/conversions/stats`);
	if (!response.ok) {
		throw new Error('Failed to fetch conversion cache stats');
	}
	return await response.json();
}

/**
 * Get cache status for all assets.
 */
export async function getAssetCacheStatus(): Promise<AssetCacheStatus[]> {
	const response = await fetch(`${API_BASE_URL}/price/cache/asset-status`);
	if (!response.ok) {
		throw new Error('Failed to fetch asset cache status');
	}
	return await response.json();
}
