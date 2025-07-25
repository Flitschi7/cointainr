/**
 * Asset Status Store
 *
 * A centralized store for asset cache status that components can subscribe to
 * instead of making individual API calls.
 */

import { writable, derived } from 'svelte/store';
import type { AssetCacheStatus } from '$lib/types';
import * as enhancedApi from '$lib/services/enhancedApi';

// Store for asset cache status
export const assetCacheStatus = writable<AssetCacheStatus[]>([]);

// Last update timestamp
let lastUpdateTime = 0;
const UPDATE_INTERVAL = 5000; // 5 seconds minimum between updates

/**
 * Refresh the asset cache status
 */
export async function refreshAssetCacheStatus(): Promise<void> {
	const now = Date.now();

	// Don't update too frequently
	if (now - lastUpdateTime < UPDATE_INTERVAL) {
		return;
	}

	try {
		const status = await enhancedApi.getAssetCacheStatus();
		assetCacheStatus.set(status);
		lastUpdateTime = now;
	} catch (error) {
		console.error('Failed to refresh asset cache status:', error);
	}
}

// Derived stores for specific queries
export const validCacheCount = derived(
	assetCacheStatus,
	($status) => $status.filter((asset) => asset.is_valid).length
);

export const totalAssetCount = derived(assetCacheStatus, ($status) => $status.length);

export const cacheEfficiency = derived([validCacheCount, totalAssetCount], ([$valid, $total]) =>
	$total > 0 ? ($valid / $total) * 100 : 0
);

// Note: Initialization and periodic refresh is handled by CacheStatusProvider
// This prevents multiple intervals from being created when the store is imported
