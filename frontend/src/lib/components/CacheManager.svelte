<script lang="ts">
import { getCacheStats, clearPriceCache, refreshAllPrices, getConversionCacheStats, clearConversionCache } from '$lib/services/api';
import type { CacheStats, RefreshAllResponse } from '$lib/services/api';
import { onMount, createEventDispatcher } from 'svelte';

const dispatch = createEventDispatcher();

let cacheStats: CacheStats | null = null;
let conversionCacheStats: { total_entries: number; fresh_entries: number; cache_age_hours: number } | null = null;
let isRefreshing = false;
let isClearingPrice = false;
let isClearingConversion = false;
let refreshResult: RefreshAllResponse | null = null;

async function loadStats() {
	try {
		cacheStats = await getCacheStats();
		conversionCacheStats = await getConversionCacheStats();
	} catch (error) {
		console.error('Failed to load cache stats:', error);
	}
}

async function handleRefreshAll() {
	if (isRefreshing) return;
	
	isRefreshing = true;
	refreshResult = null;
	
	try {
		refreshResult = await refreshAllPrices();
		await loadStats();
		dispatch('pricesRefreshed', refreshResult);
	} catch (error) {
		console.error('Failed to refresh prices:', error);
		alert('Failed to refresh prices. Please try again.');
	} finally {
		isRefreshing = false;
	}
}

async function handleClearCache() {
	if (isClearingPrice) return;
	
	isClearingPrice = true;
	
	try {
		await clearPriceCache();
		await loadStats();
		dispatch('cacheCleared');
		alert('Price cache cleared successfully!');
	} catch (error) {
		console.error('Failed to clear price cache:', error);
		alert('Failed to clear price cache. Please try again.');
	} finally {
		isClearingPrice = false;
	}
}

async function handleClearConversionCache() {
	if (isClearingConversion) return;
	
	isClearingConversion = true;
	
	try {
		await clearConversionCache();
		await loadStats();
		dispatch('conversionCacheCleared');
		alert('Conversion cache cleared successfully!');
	} catch (error) {
		console.error('Failed to clear conversion cache:', error);
		alert('Failed to clear conversion cache. Please try again.');
	} finally {
		isClearingConversion = false;
	}
}

onMount(() => {
	loadStats();
});
</script>

<div class="bg-surface rounded-lg p-4">
	<h3 class="font-semibold text-lg mb-3">Price Cache Management</h3>
	
	<!-- Cache Statistics -->
	{#if cacheStats || conversionCacheStats}
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
			{#if cacheStats}
				<div class="bg-background rounded p-2">
					<div class="text-gray-400">Price Cache</div>
					<div class="font-mono text-lg">{cacheStats.fresh_entries}/{cacheStats.total_entries}</div>
					<div class="text-xs text-gray-400">({cacheStats.cache_age_minutes}min TTL)</div>
				</div>
				<div class="bg-background rounded p-2">
					<div class="text-gray-400">Stock Prices</div>
					<div class="font-mono text-lg">{cacheStats.stock_entries}</div>
				</div>
				<div class="bg-background rounded p-2">
					<div class="text-gray-400">Crypto Prices</div>
					<div class="font-mono text-lg">{cacheStats.crypto_entries}</div>
				</div>
			{/if}
			{#if conversionCacheStats}
				<div class="bg-background rounded p-2">
					<div class="text-gray-400">Conversion Cache</div>
					<div class="font-mono text-lg">{conversionCacheStats.fresh_entries}/{conversionCacheStats.total_entries}</div>
					<div class="text-xs text-gray-400">({conversionCacheStats.cache_age_hours}h TTL)</div>
				</div>
			{/if}
		</div>
	{/if}
	
	<!-- Actions -->
	<div class="flex flex-wrap gap-2 mb-4">
		<button 
			on:click={handleRefreshAll}
			disabled={isRefreshing}
			class="bg-primary hover:opacity-80 disabled:opacity-50 text-white font-bold py-2 px-4 rounded"
		>
			{isRefreshing ? 'Refreshing...' : 'Refresh All Prices'}
		</button>
		
		<button 
			on:click={handleClearCache}
			disabled={isClearingPrice}
			class="bg-loss hover:opacity-80 disabled:opacity-50 text-white font-bold py-2 px-4 rounded"
		>
			{isClearingPrice ? 'Clearing...' : 'Clear Price Cache'}
		</button>
		
		<button 
			on:click={handleClearConversionCache}
			disabled={isClearingConversion}
			class="bg-loss hover:opacity-80 disabled:opacity-50 text-white font-bold py-2 px-4 rounded"
		>
			{isClearingConversion ? 'Clearing...' : 'Clear Conversion Cache'}
		</button>
		
		<button 
			on:click={loadStats}
			class="bg-surface hover:bg-gray-600 text-white font-bold py-2 px-4 rounded border border-gray-500"
		>
			Reload Stats
		</button>
	</div>
	
	<!-- Refresh Results -->
	{#if refreshResult}
		<div class="bg-background rounded p-3 text-sm">
			<div class="text-primary font-semibold mb-1">Last Refresh Results</div>
			<div class="text-profit">✅ Successfully refreshed: {refreshResult.refreshed} assets</div>
			{#if refreshResult.errors > 0}
				<div class="text-loss">❌ Errors: {refreshResult.errors} assets</div>
				<details class="mt-2">
					<summary class="cursor-pointer text-gray-300">Show error details</summary>
					<div class="mt-2 max-h-32 overflow-y-auto">
						{#each refreshResult.error_details as error}
							<div class="text-xs text-loss mb-1">
								<strong>{error.symbol}</strong> (ID: {error.asset_id}): {error.error}
							</div>
						{/each}
					</div>
				</details>
			{/if}
		</div>
	{/if}
</div>
