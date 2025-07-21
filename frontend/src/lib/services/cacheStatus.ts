import { getAssetCacheStatus } from './api';
import type { AssetCacheStatus } from '$lib/types';

/**
 * Cache status indicator types
 */
export enum CacheStatusType {
	FRESH = 'fresh',
	VALID = 'valid',
	EXPIRED = 'expired',
	UNKNOWN = 'unknown'
}

/**
 * Cache status service for managing cache status display and validation
 */
export class CacheStatusService {
	private cacheStatusMap: Map<number, AssetCacheStatus> = new Map();
	private lastFetchTime: number = 0;
	private readonly CACHE_REFRESH_INTERVAL = 60000; // 1 minute in milliseconds

	/**
	 * Fetch cache status for all assets and store in the cache status map
	 */
	async fetchAllCacheStatus(): Promise<Map<number, AssetCacheStatus>> {
		try {
			const cacheStatuses = await getAssetCacheStatus();

			// Process each cache status to add derived fields
			const enhancedStatuses = cacheStatuses.map((status) => {
				const isValid = this.isCacheValid(status);
				const expiresAt = this.calculateExpirationTime(status);

				return {
					...status,
					is_valid: isValid,
					expires_at: expiresAt
				};
			});

			// Update the cache status map
			this.cacheStatusMap.clear();
			enhancedStatuses.forEach((status) => {
				this.cacheStatusMap.set(status.asset_id, status);
			});

			this.lastFetchTime = Date.now();
			return this.cacheStatusMap;
		} catch (error) {
			console.error('Failed to fetch cache status:', error);
			throw error;
		}
	}

	/**
	 * Get cache status for an individual asset
	 * @param assetId The asset ID to get cache status for
	 * @returns The cache status for the asset or null if not found
	 */
	async getCacheStatusForAsset(assetId: number): Promise<AssetCacheStatus | null> {
		// Refresh cache status if it's stale
		if (Date.now() - this.lastFetchTime > this.CACHE_REFRESH_INTERVAL) {
			await this.fetchAllCacheStatus();
		}

		return this.cacheStatusMap.get(assetId) || null;
	}

	/**
	 * Check if cache is still valid based on TTL
	 * @param cacheStatus The cache status to check
	 * @returns True if cache is valid, false otherwise
	 */
	isCacheValid(cacheStatus: { cached_at: string | null; cache_ttl_minutes: number }): boolean {
		if (!cacheStatus.cached_at) {
			return false;
		}

		const cachedAt = new Date(cacheStatus.cached_at).getTime();
		const now = Date.now();
		const ttlMs = cacheStatus.cache_ttl_minutes * 60 * 1000;

		return now - cachedAt < ttlMs;
	}

	/**
	 * Calculate when the cache expires
	 * @param cacheStatus The cache status to calculate expiration for
	 * @returns ISO string of expiration time or null if no cache
	 */
	calculateExpirationTime(cacheStatus: {
		cached_at: string | null;
		cache_ttl_minutes: number;
	}): string | null {
		if (!cacheStatus.cached_at) {
			return null;
		}

		const cachedAt = new Date(cacheStatus.cached_at);
		const expiresAt = new Date(cachedAt.getTime() + cacheStatus.cache_ttl_minutes * 60 * 1000);

		return expiresAt.toISOString();
	}

	/**
	 * Format cache age for display
	 * @param cachedAt ISO string of when the cache was created
	 * @returns Formatted string showing cache age (e.g., "2 minutes ago")
	 */
	formatCacheAge(cachedAt: string | null): string {
		if (!cachedAt) {
			return 'Never cached';
		}

		const cachedTime = new Date(cachedAt).getTime();
		const now = Date.now();
		const diffMs = now - cachedTime;

		// Convert to appropriate time unit
		if (diffMs < 60000) {
			// Less than a minute
			const seconds = Math.floor(diffMs / 1000);
			return `${seconds} second${seconds !== 1 ? 's' : ''} ago`;
		} else if (diffMs < 3600000) {
			// Less than an hour
			const minutes = Math.floor(diffMs / 60000);
			return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
		} else if (diffMs < 86400000) {
			// Less than a day
			const hours = Math.floor(diffMs / 3600000);
			return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
		} else {
			// Days or more
			const days = Math.floor(diffMs / 86400000);
			return `${days} day${days !== 1 ? 's' : ''} ago`;
		}
	}

	/**
	 * Format time until cache expiration
	 * @param expiresAt ISO string of when the cache expires
	 * @returns Formatted string showing time until expiration (e.g., "Expires in 13 minutes")
	 */
	formatTimeUntilExpiration(expiresAt: string | null): string {
		if (!expiresAt) {
			return 'No expiration';
		}

		const expirationTime = new Date(expiresAt).getTime();
		const now = Date.now();
		const diffMs = expirationTime - now;

		if (diffMs <= 0) {
			return 'Expired';
		}

		// Convert to appropriate time unit
		if (diffMs < 60000) {
			// Less than a minute
			const seconds = Math.floor(diffMs / 1000);
			return `Expires in ${seconds} second${seconds !== 1 ? 's' : ''}`;
		} else if (diffMs < 3600000) {
			// Less than an hour
			const minutes = Math.floor(diffMs / 60000);
			return `Expires in ${minutes} minute${minutes !== 1 ? 's' : ''}`;
		} else if (diffMs < 86400000) {
			// Less than a day
			const hours = Math.floor(diffMs / 3600000);
			return `Expires in ${hours} hour${hours !== 1 ? 's' : ''}`;
		} else {
			// Days or more
			const days = Math.floor(diffMs / 86400000);
			return `Expires in ${days} day${days !== 1 ? 's' : ''}`;
		}
	}

	/**
	 * Get cache status type for display
	 * @param cacheStatus The cache status to get type for
	 * @returns The cache status type (fresh, valid, expired, unknown)
	 */
	getCacheStatusType(cacheStatus: AssetCacheStatus | null): CacheStatusType {
		if (!cacheStatus || !cacheStatus.cached_at) {
			return CacheStatusType.UNKNOWN;
		}

		// If cached within the last minute, consider it fresh
		const cachedAt = new Date(cacheStatus.cached_at).getTime();
		const now = Date.now();
		const isFresh = now - cachedAt < 60000; // 1 minute

		if (isFresh) {
			return CacheStatusType.FRESH;
		}

		if (cacheStatus.is_valid) {
			return CacheStatusType.VALID;
		}

		return CacheStatusType.EXPIRED;
	}

	/**
	 * Get CSS class for cache status indicator
	 * @param statusType The cache status type
	 * @returns CSS class name for styling the indicator
	 */
	getCacheStatusClass(statusType: CacheStatusType): string {
		switch (statusType) {
			case CacheStatusType.FRESH:
				return 'cache-status-fresh';
			case CacheStatusType.VALID:
				return 'cache-status-valid';
			case CacheStatusType.EXPIRED:
				return 'cache-status-expired';
			case CacheStatusType.UNKNOWN:
			default:
				return 'cache-status-unknown';
		}
	}

	/**
	 * Get display text for cache status
	 * @param statusType The cache status type
	 * @returns Human-readable status text
	 */
	getCacheStatusText(statusType: CacheStatusType): string {
		switch (statusType) {
			case CacheStatusType.FRESH:
				return 'Fresh';
			case CacheStatusType.VALID:
				return 'Cached';
			case CacheStatusType.EXPIRED:
				return 'Expired';
			case CacheStatusType.UNKNOWN:
			default:
				return 'Unknown';
		}
	}

	/**
	 * Reset the cache status service
	 */
	reset(): void {
		this.cacheStatusMap.clear();
		this.lastFetchTime = 0;
	}
}

// Export a singleton instance
export const cacheStatusService = new CacheStatusService();
