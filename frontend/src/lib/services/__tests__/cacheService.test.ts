import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { CacheService } from '../cacheService';

describe('CacheService', () => {
	let cacheService: CacheService;

	beforeEach(() => {
		// Create a new cache service before each test with a short TTL for testing
		cacheService = new CacheService(1000); // 1 second TTL
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('should store and retrieve data from cache', () => {
		const key = 'test-key';
		const data = { value: 'test-value' };

		cacheService.set(key, data);

		const cachedEntry = cacheService.get(key);
		expect(cachedEntry).toBeDefined();
		expect(cachedEntry?.data).toEqual(data);
		expect(cachedEntry?.isStale).toBe(false);
	});

	it('should mark cache as expired after TTL', () => {
		const key = 'test-key';
		const data = { value: 'test-value' };

		cacheService.set(key, data);

		// Advance time past TTL
		vi.advanceTimersByTime(1500);

		expect(cacheService.isExpired(key)).toBe(true);

		const cachedEntry = cacheService.get(key);
		expect(cachedEntry?.isStale).toBe(true);
	});

	it('should fetch fresh data when cache is expired or forced', async () => {
		const key = 'test-key';
		const initialData = { value: 'initial' };
		const freshData = { value: 'fresh' };

		// Mock fetch function
		const fetchFn = vi.fn().mockResolvedValue(freshData);

		// Set initial data
		cacheService.set(key, initialData);

		// First call should use cache
		const result1 = await cacheService.getOrFetch(key, fetchFn);
		expect(result1).toEqual(initialData);
		expect(fetchFn).not.toHaveBeenCalled();

		// Force refresh should call fetch
		const result2 = await cacheService.getOrFetch(key, fetchFn, { forceRefresh: true });
		expect(result2).toEqual(freshData);
		expect(fetchFn).toHaveBeenCalledTimes(1);

		// Advance time past TTL
		vi.advanceTimersByTime(1500);

		// Expired cache should call fetch
		const result3 = await cacheService.getOrFetch(key, fetchFn);
		expect(result3).toEqual(freshData);
		expect(fetchFn).toHaveBeenCalledTimes(2);
	});

	it('should return cached data when fetch fails', async () => {
		const key = 'test-key';
		const cachedData = { value: 'cached' };

		// Set initial data
		cacheService.set(key, cachedData);

		// Mock fetch function that fails
		const fetchFn = vi.fn().mockRejectedValue(new Error('Fetch failed'));

		// Should return cached data even though fetch fails
		const result = await cacheService.getOrFetch(key, fetchFn, { forceRefresh: true });
		expect(result).toEqual(cachedData);
		expect(fetchFn).toHaveBeenCalledTimes(1);

		// Cached entry should be marked as stale
		const cachedEntry = cacheService.get(key);
		expect(cachedEntry?.isStale).toBe(true);
	});

	it('should track hit and miss counts', async () => {
		const key = 'test-key';
		const data = { value: 'test' };

		// Mock fetch function
		const fetchFn = vi.fn().mockResolvedValue(data);

		// First call should miss
		await cacheService.getOrFetch(key, fetchFn);
		expect(cacheService.getMissCount(key)).toBe(1);
		expect(cacheService.getHitCount(key)).toBe(0);

		// Second call should hit
		await cacheService.getOrFetch(key, fetchFn);
		expect(cacheService.getMissCount(key)).toBe(1);
		expect(cacheService.getHitCount(key)).toBe(1);

		// Force refresh should miss
		await cacheService.getOrFetch(key, fetchFn, { forceRefresh: true });
		expect(cacheService.getMissCount(key)).toBe(2);
		expect(cacheService.getHitCount(key)).toBe(1);
	});

	it('should clear cache entries', () => {
		cacheService.set('key1', 'value1');
		cacheService.set('key2', 'value2');
		cacheService.set('prefix-key3', 'value3');
		cacheService.set('prefix-key4', 'value4');

		expect(cacheService.getKeys().length).toBe(4);

		// Clear single entry
		cacheService.clearCache('key1');
		expect(cacheService.has('key1')).toBe(false);
		expect(cacheService.getKeys().length).toBe(3);

		// Clear by prefix
		const cleared = cacheService.clearCacheByPrefix('prefix-');
		expect(cleared).toBe(2);
		expect(cacheService.getKeys().length).toBe(1);

		// Clear all
		cacheService.clearAllCache();
		expect(cacheService.getKeys().length).toBe(0);
	});

	it('should calculate cache statistics', () => {
		// Add some cache entries
		cacheService.set('key1', 'value1');
		cacheService.set('key2', 'value2');
		cacheService.set('prefix-key3', 'value3');

		// Simulate some hits and misses
		cacheService.getOrFetch('key1', () => Promise.resolve('value1'));
		cacheService.getOrFetch('key2', () => Promise.resolve('value2'));
		cacheService.getOrFetch('key2', () => Promise.resolve('value2'));
		cacheService.getOrFetch('missing', () => Promise.resolve('missing'));

		// Get overall stats
		const stats = cacheService.getCacheStats();
		expect(stats.count).toBe(3);

		// Get stats for prefix
		const prefixStats = cacheService.getCacheStats('prefix-');
		expect(prefixStats.count).toBe(1);
	});
});
