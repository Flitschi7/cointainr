/**
 * CacheService - A centralized cache management service for the frontend
 *
 * This service provides a generic caching mechanism with TTL support,
 * cache validation, and statistics tracking. It's designed to be used
 * by other services to implement a cache-first approach for API calls.
 */

/**
 * Interface for cache entry with data, timestamp, and staleness indicator
 */
export interface CacheEntry<T> {
	data: T;
	timestamp: number;
	isStale: boolean;
}

/**
 * Interface for cache options
 */
export interface CacheOptions {
	ttl: number; // Time-to-live in milliseconds
	forceRefresh?: boolean;
}

/**
 * Interface for cache statistics
 */
export interface CacheStats {
	count: number;
	averageAge: number;
	oldestEntry: number;
	newestEntry: number;
	hitCount: number;
	missCount: number;
	hitRate: number;
}

/**
 * CacheService class for managing cached data with TTL support
 */
export class CacheService {
	// Store cache data in memory
	private cache: Map<string, CacheEntry<any>> = new Map();
	private hitCount: Map<string, number> = new Map();
	private missCount: Map<string, number> = new Map();
	private defaultTTL: number = 15 * 60 * 1000; // Default 15 minutes in milliseconds
	private storageKey = 'cointainr_cache';
	private statsKey = 'cointainr_cache_stats';

	/**
	 * Constructor with optional default TTL
	 * @param defaultTTL Default time-to-live in milliseconds
	 */
	constructor(defaultTTL?: number) {
		if (defaultTTL) {
			this.defaultTTL = defaultTTL;
		}

		// Load cache from localStorage on initialization
		this.loadFromStorage();
	}

	/**
	 * Get data from cache or fetch from API
	 * @param key Cache key
	 * @param fetchFn Function to fetch data if not in cache
	 * @param options Cache options (TTL, forceRefresh)
	 * @returns Promise with the data
	 */
	async getOrFetch<T>(
		key: string,
		fetchFn: () => Promise<T>,
		options?: Partial<CacheOptions>
	): Promise<T> {
		const ttl = options?.ttl || this.defaultTTL;
		const forceRefresh = options?.forceRefresh || false;

		// Determine cache type for performance tracking
		const cacheType = key.includes('price') ? 'price' : 'conversion';

		// Check if we should use cache
		if (!forceRefresh && this.has(key)) {
			const entry = this.get<T>(key);
			if (entry) {
				// Increment hit count
				this.incrementHitCount(key);

				// Track in performance monitoring
				try {
					import('../services/performanceMonitoring').then((module) => {
						module.trackCacheAccess(cacheType, true);
					});
				} catch (e) {
					// Ignore import errors
				}

				return entry.data;
			}
		}

		// Cache miss or force refresh, fetch fresh data
		try {
			// Increment miss count
			this.incrementMissCount(key);

			// Track in performance monitoring
			try {
				import('../services/performanceMonitoring').then((module) => {
					module.trackCacheAccess(cacheType, false);
				});
			} catch (e) {
				// Ignore import errors
			}

			// Fetch fresh data
			const data = await fetchFn();

			// Store in cache
			this.set(key, data, ttl);

			return data;
		} catch (error) {
			// If fetch fails but we have cached data, return it even if stale
			if (this.has(key)) {
				console.warn(`Failed to fetch fresh data for ${key}, using cached data instead`, error);
				const entry = this.get<T>(key);
				if (entry) {
					// Mark as stale
					entry.isStale = true;
					this.cache.set(key, entry);
					return entry.data;
				}
			}

			// No cached data available, rethrow the error
			throw error;
		}
	}

	/**
	 * Set data in cache with TTL
	 * @param key Cache key
	 * @param data Data to cache
	 * @param ttl Time-to-live in milliseconds (optional, uses default if not provided)
	 */
	set<T>(key: string, data: T, ttl?: number): void {
		const timestamp = Date.now();
		const entry: CacheEntry<T> = {
			data,
			timestamp,
			isStale: false
		};

		this.cache.set(key, entry);

		// Save to localStorage
		this.saveToStorage();
	}

	/**
	 * Get data from cache
	 * @param key Cache key
	 * @returns Cache entry or undefined if not found
	 */
	get<T>(key: string): CacheEntry<T> | undefined {
		const entry = this.cache.get(key) as CacheEntry<T> | undefined;

		if (entry) {
			// Check if entry is expired
			if (this.isExpired(key)) {
				entry.isStale = true;
			}
		}

		return entry;
	}

	/**
	 * Check if key exists in cache
	 * @param key Cache key
	 * @returns True if key exists in cache
	 */
	has(key: string): boolean {
		return this.cache.has(key);
	}

	/**
	 * Check if cache entry is expired
	 * @param key Cache key
	 * @param ttl Optional TTL to override default
	 * @returns True if cache entry is expired
	 */
	isExpired(key: string, ttl?: number): boolean {
		const entry = this.cache.get(key);
		if (!entry) {
			return true;
		}

		const now = Date.now();
		const expiryTime = entry.timestamp + (ttl || this.defaultTTL);

		return now > expiryTime;
	}

	/**
	 * Check if cache is valid (exists and not expired)
	 * @param key Cache key
	 * @param ttl Optional TTL to override default
	 * @returns True if cache is valid
	 */
	isCacheValid(key: string, ttl?: number): boolean {
		return this.has(key) && !this.isExpired(key, ttl);
	}

	/**
	 * Get cache age in milliseconds
	 * @param key Cache key
	 * @returns Cache age in milliseconds or -1 if not found
	 */
	getCacheAge(key: string): number {
		const entry = this.cache.get(key);
		if (!entry) {
			return -1;
		}

		return Date.now() - entry.timestamp;
	}

	/**
	 * Format cache age for display
	 * @param key Cache key
	 * @returns Formatted string showing cache age (e.g., "2 minutes ago")
	 */
	formatCacheAge(key: string): string {
		const ageMs = this.getCacheAge(key);

		if (ageMs < 0) {
			return 'Not cached';
		}

		// Convert to appropriate time unit
		if (ageMs < 60000) {
			// Less than a minute
			const seconds = Math.floor(ageMs / 1000);
			return `${seconds} second${seconds !== 1 ? 's' : ''} ago`;
		} else if (ageMs < 3600000) {
			// Less than an hour
			const minutes = Math.floor(ageMs / 60000);
			return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
		} else if (ageMs < 86400000) {
			// Less than a day
			const hours = Math.floor(ageMs / 3600000);
			return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
		} else {
			// Days or more
			const days = Math.floor(ageMs / 86400000);
			return `${days} day${days !== 1 ? 's' : ''} ago`;
		}
	}

	/**
	 * Get time until cache expiration
	 * @param key Cache key
	 * @param ttl Optional TTL to override default
	 * @returns Time until expiration in milliseconds or -1 if not found
	 */
	getTimeUntilExpiration(key: string, ttl?: number): number {
		const entry = this.cache.get(key);
		if (!entry) {
			return -1;
		}

		const expiryTime = entry.timestamp + (ttl || this.defaultTTL);
		return expiryTime - Date.now();
	}

	/**
	 * Format time until cache expiration
	 * @param key Cache key
	 * @param ttl Optional TTL to override default
	 * @returns Formatted string showing time until expiration
	 */
	formatTimeUntilExpiration(key: string, ttl?: number): string {
		const timeMs = this.getTimeUntilExpiration(key, ttl);

		if (timeMs < 0) {
			return 'Expired';
		}

		// Convert to appropriate time unit
		if (timeMs < 60000) {
			// Less than a minute
			const seconds = Math.floor(timeMs / 1000);
			return `Expires in ${seconds} second${seconds !== 1 ? 's' : ''}`;
		} else if (timeMs < 3600000) {
			// Less than an hour
			const minutes = Math.floor(timeMs / 60000);
			return `Expires in ${minutes} minute${minutes !== 1 ? 's' : ''}`;
		} else if (timeMs < 86400000) {
			// Less than a day
			const hours = Math.floor(timeMs / 3600000);
			return `Expires in ${hours} hour${hours !== 1 ? 's' : ''}`;
		} else {
			// Days or more
			const days = Math.floor(timeMs / 86400000);
			return `Expires in ${days} day${days !== 1 ? 's' : ''}`;
		}
	}

	/**
	 * Clear specific cache entry
	 * @param key Cache key
	 * @returns True if entry was found and cleared
	 */
	clearCache(key: string): boolean {
		const result = this.cache.delete(key);
		if (result) {
			this.saveToStorage();
		}
		return result;
	}

	/**
	 * Clear all cache entries
	 */
	clearAllCache(): void {
		this.cache.clear();
		this.hitCount.clear();
		this.missCount.clear();
		this.clearStorage();
	}

	/**
	 * Clear all cache entries with a specific prefix
	 * @param prefix Key prefix to match
	 * @returns Number of entries cleared
	 */
	clearCacheByPrefix(prefix: string): number {
		let count = 0;
		for (const key of this.cache.keys()) {
			if (key.startsWith(prefix)) {
				this.cache.delete(key);
				count++;
			}
		}
		if (count > 0) {
			this.saveToStorage();
		}
		return count;
	}

	/**
	 * Increment hit count for a key
	 * @param key Cache key
	 */
	private incrementHitCount(key: string): void {
		const current = this.hitCount.get(key) || 0;
		this.hitCount.set(key, current + 1);
		// Save stats periodically (every 10th hit to avoid too frequent saves)
		if ((current + 1) % 10 === 0) {
			this.saveToStorage();
		}
	}

	/**
	 * Increment miss count for a key
	 * @param key Cache key
	 */
	private incrementMissCount(key: string): void {
		const current = this.missCount.get(key) || 0;
		this.missCount.set(key, current + 1);
		// Save stats periodically (every 10th miss to avoid too frequent saves)
		if ((current + 1) % 10 === 0) {
			this.saveToStorage();
		}
	}

	/**
	 * Get hit count for a key
	 * @param key Cache key
	 * @returns Hit count
	 */
	getHitCount(key: string): number {
		return this.hitCount.get(key) || 0;
	}

	/**
	 * Get miss count for a key
	 * @param key Cache key
	 * @returns Miss count
	 */
	getMissCount(key: string): number {
		return this.missCount.get(key) || 0;
	}

	/**
	 * Get hit rate for a key
	 * @param key Cache key
	 * @returns Hit rate (0-1)
	 */
	getHitRate(key: string): number {
		const hits = this.getHitCount(key);
		const misses = this.getMissCount(key);
		const total = hits + misses;

		if (total === 0) {
			return 0;
		}

		return hits / total;
	}

	/**
	 * Get cache statistics
	 * @param prefix Optional prefix to filter keys
	 * @returns Cache statistics
	 */
	getCacheStats(prefix?: string): CacheStats {
		let keys = Array.from(this.cache.keys());

		// Filter by prefix if provided
		if (prefix) {
			keys = keys.filter((key) => key.startsWith(prefix));
		}

		// Calculate statistics
		const count = keys.length;
		let totalAge = 0;
		let oldestEntry = Infinity;
		let newestEntry = 0;
		let totalHits = 0;
		let totalMisses = 0;

		for (const key of keys) {
			const age = this.getCacheAge(key);
			totalAge += age;
			oldestEntry = Math.min(oldestEntry, age);
			newestEntry = Math.max(newestEntry, age);

			totalHits += this.getHitCount(key);
			totalMisses += this.getMissCount(key);
		}

		const averageAge = count > 0 ? totalAge / count : 0;
		const hitRate = totalHits + totalMisses > 0 ? totalHits / (totalHits + totalMisses) : 0;

		return {
			count,
			averageAge,
			oldestEntry: count > 0 ? oldestEntry : 0,
			newestEntry,
			hitCount: totalHits,
			missCount: totalMisses,
			hitRate
		};
	}

	/**
	 * Get all keys in cache
	 * @param prefix Optional prefix to filter keys
	 * @returns Array of cache keys
	 */
	getKeys(prefix?: string): string[] {
		const keys = Array.from(this.cache.keys());

		if (prefix) {
			return keys.filter((key) => key.startsWith(prefix));
		}

		return keys;
	}

	/**
	 * Get all entries in cache
	 * @param prefix Optional prefix to filter keys
	 * @returns Map of cache entries
	 */
	getEntries<T>(prefix?: string): Map<string, CacheEntry<T>> {
		const entries = new Map<string, CacheEntry<T>>();

		for (const [key, value] of this.cache.entries()) {
			if (!prefix || key.startsWith(prefix)) {
				entries.set(key, value as CacheEntry<T>);
			}
		}

		return entries;
	}

	/**
	 * Load cache from localStorage
	 */
	private loadFromStorage(): void {
		if (typeof window === 'undefined' || !window.localStorage) {
			return;
		}

		try {
			// Load cache data
			const cacheData = localStorage.getItem(this.storageKey);
			if (cacheData) {
				const parsed = JSON.parse(cacheData);
				// Convert plain object back to Map and filter out expired entries
				const now = Date.now();
				for (const [key, entry] of Object.entries(parsed)) {
					const cacheEntry = entry as CacheEntry<any>;
					// Only load non-expired entries
					if (now - cacheEntry.timestamp < this.defaultTTL) {
						this.cache.set(key, cacheEntry);
					}
				}
			}

			// Load stats
			const statsData = localStorage.getItem(this.statsKey);
			if (statsData) {
				const parsed = JSON.parse(statsData);
				this.hitCount = new Map(Object.entries(parsed.hitCount || {}));
				this.missCount = new Map(Object.entries(parsed.missCount || {}));
			}
		} catch (error) {
			console.warn('Failed to load cache from localStorage:', error);
			// Clear corrupted data
			this.clearStorage();
		}
	}

	/**
	 * Save cache to localStorage
	 */
	private saveToStorage(): void {
		if (typeof window === 'undefined' || !window.localStorage) {
			return;
		}

		try {
			// Save cache data (convert Map to plain object)
			const cacheData = Object.fromEntries(this.cache.entries());
			localStorage.setItem(this.storageKey, JSON.stringify(cacheData));

			// Save stats
			const statsData = {
				hitCount: Object.fromEntries(this.hitCount.entries()),
				missCount: Object.fromEntries(this.missCount.entries())
			};
			localStorage.setItem(this.statsKey, JSON.stringify(statsData));
		} catch (error) {
			console.warn('Failed to save cache to localStorage:', error);
		}
	}

	/**
	 * Clear localStorage cache
	 */
	private clearStorage(): void {
		if (typeof window === 'undefined' || !window.localStorage) {
			return;
		}

		try {
			localStorage.removeItem(this.storageKey);
			localStorage.removeItem(this.statsKey);
		} catch (error) {
			console.warn('Failed to clear cache from localStorage:', error);
		}
	}
}

// Export a singleton instance with default TTL
export const cacheService = new CacheService();
