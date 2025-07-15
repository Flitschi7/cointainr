import { getAssets, getAssetCacheStatus } from '$lib/services/api';

/** @type {import('./$types').PageLoad} */
export async function load() {
	try {
		// Load both assets and cache status in parallel
		const [assets, cacheStatus] = await Promise.all([getAssets(), getAssetCacheStatus()]);

		return {
			assets,
			cacheStatus
		};
	} catch (error) {
		console.error('Failed to load page data:', error);
		return {
			assets: [],
			cacheStatus: []
		};
	}
}
