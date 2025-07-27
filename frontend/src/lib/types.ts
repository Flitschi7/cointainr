/**
 * Enum for supported asset types.
 */
export type AssetType = 'cash' | 'stock' | 'crypto' | 'derivative';

/**
 * Asset interface representing a financial asset.
 */
export interface Asset {
	id: number;
	type: AssetType;
	name: string;
	assetname?: string | null;
	quantity: number;
	symbol: string | null;
	currency: string | null;
	purchase_price: number | null;
	buy_currency: string | null;
}

/**
 * Price response interface from the API.
 */
export interface PriceResponse {
	symbol: string;
	price: number;
	currency: string;
	cached?: boolean;
	fetched_at?: string;
	source?: string;
}

/**
 * Currency conversion response interface from the API.
 */
export interface ConversionResponse {
	from: string;
	to: string;
	amount: number;
	converted: number;
	rate: number;
	cached?: boolean;
	fetched_at?: string;
	source?: string;
	last_update?: string;
	next_update?: string;
}

/**
 * Conversion rate response interface from the API.
 */
export interface ConversionRateResponse {
	from: string;
	to: string;
	rate: number;
	cached?: boolean;
	fetched_at?: string;
	source?: string;
	last_update?: string;
	next_update?: string;
}

/**
 * Cache statistics interface from the API.
 */
export interface CacheStats {
	total_entries: number;
	fresh_entries: number;
	stock_entries: number;
	crypto_entries: number;
	cache_age_minutes: number;
}

/**
 * Response interface for refreshing all prices.
 */
export interface RefreshAllResponse {
	refreshed: number;
	errors: number;
	results: Array<{
		asset_id: number;
		symbol: string;
		type: string;
		price: number;
		currency: string;
		source: string;
	}>;
	error_details: Array<{
		asset_id: number;
		symbol: string;
		error: string;
	}>;
}

/**
 * Asset cache status interface from the API.
 */
export interface AssetCacheStatus {
	asset_id: number;
	symbol: string | null;
	type: string;
	cached_at: string | null;
	cache_ttl_minutes: number;
	is_valid: boolean;
	expires_at: string | null;
	cache_age_minutes: number | null;
	needs_refresh: boolean;
}
