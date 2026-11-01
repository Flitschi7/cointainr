import { afterEach, describe, expect, it, vi } from 'vitest';
import { CacheService } from '../cacheService';

// Simulates the monitoring module failing to load, e.g. after test teardown.
vi.mock('../performanceMonitoring', () => {
	throw new Error('Monitoring unavailable');
});

describe('Cache access tracking', () => {
	const unhandled: unknown[] = [];
	const recordUnhandled = (reason: unknown) => unhandled.push(reason);

	afterEach(() => {
		process.off('unhandledRejection', recordUnhandled);
		unhandled.length = 0;
	});

	it('does not leak a rejection when the monitoring module cannot load', async () => {
		process.on('unhandledRejection', recordUnhandled);
		const cache = new CacheService();

		await cache.getOrFetch('price_TEST', async () => 1);
		expect(await cache.getOrFetch('price_TEST', async () => 2)).toBe(1);
		await new Promise((resolve) => setTimeout(resolve, 20));

		expect(unhandled).toEqual([]);
	});
});
