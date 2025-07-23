<script lang="ts">
	import { onMount } from 'svelte';
	import {
		assetCacheStatuses,
		priceCacheStats,
		conversionCacheStats,
		lastCacheRefresh,
		cacheRefreshInProgress
	} from '$lib/stores/cacheStore';
	import { refreshAssetCacheStatus } from '$lib/stores/assetStatusStore';
	import { cacheStatusService } from '$lib/services/cacheStatus';
	import { clearPriceCache, clearConversionCache, refreshAllPrices } from '$lib/services/api';
	import CacheHealthIndicator from './CacheHealthIndicator.svelte';

	let refreshing = false;
	let clearingPriceCache = false;
	let clearingConversionCache = false;
	let errorMessage: string | null = null;
	let successMessage: string | null = null;

	// Format the last refresh time
	function formatLastRefresh(date: Date | null): string {
		if (!date) return 'Never';
		return date.toLocaleString();
	}

	// Handle refresh all prices
	async function handleRefreshAllPrices(): Promise<void> {
		refreshing = true;
		errorMessage = null;
		successMessage = null;

		try {
			await refreshAllPrices();
			successMessage = 'Successfully refreshed all prices';
			// Refresh cache status after prices are refreshed
			await refreshAssetCacheStatus();
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Failed to refresh prices';
		} finally {
			refreshing = false;
		}
	}

	// Handle clear price cache
	async function handleClearPriceCache(): Promise<void> {
		clearingPriceCache = true;
		errorMessage = null;
		successMessage = null;

		try {
			await clearPriceCache();
			successMessage = 'Successfully cleared price cache';
			// Refresh cache status after cache is cleared
			await refreshAssetCacheStatus();
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Failed to clear price cache';
		} finally {
			clearingPriceCache = false;
		}
	}

	// Handle clear conversion cache
	async function handleClearConversionCache(): Promise<void> {
		clearingConversionCache = true;
		errorMessage = null;
		successMessage = null;

		try {
			await clearConversionCache();
			successMessage = 'Successfully cleared conversion cache';
			// Refresh cache status after cache is cleared
			await refreshAssetCacheStatus();
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Failed to clear conversion cache';
		} finally {
			clearingConversionCache = false;
		}
	}

	// Clear messages after a delay
	function clearMessages(): void {
		setTimeout(() => {
			errorMessage = null;
			successMessage = null;
		}, 5000);
	}

	// Watch for message changes
	let messageTimeoutId: number | null = null;
	$: if (errorMessage || successMessage) {
		if (messageTimeoutId) {
			clearTimeout(messageTimeoutId);
		}
		messageTimeoutId = window.setTimeout(() => {
			errorMessage = null;
			successMessage = null;
			messageTimeoutId = null;
		}, 5000);
	}

	// Initial load
	onMount(() => {
		// Note: Cache status is automatically managed by CacheStatusProvider
		// No need to refresh here
	});
</script>

<div class="cache-management-panel rounded-md border p-4">
	<h2 class="mb-4 text-xl font-semibold">Cache Management</h2>

	<div class="mb-4">
		<CacheHealthIndicator showDetails={true} />
	</div>

	{#if errorMessage}
		<div class="mb-4 rounded border border-red-400 bg-red-100 px-4 py-2 text-red-700">
			{errorMessage}
		</div>
	{/if}

	{#if successMessage}
		<div class="mb-4 rounded border border-green-400 bg-green-100 px-4 py-2 text-green-700">
			{successMessage}
		</div>
	{/if}

	<div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
		<!-- Price Cache Stats -->
		<div class="rounded border bg-white p-4">
			<h3 class="mb-2 font-medium">Price Cache</h3>
			{#if $priceCacheStats}
				<div class="text-sm">
					<div>Total entries: {$priceCacheStats.total_entries}</div>
					<div>Fresh entries: {$priceCacheStats.fresh_entries}</div>
					<div>Stock entries: {$priceCacheStats.stock_entries}</div>
					<div>Crypto entries: {$priceCacheStats.crypto_entries}</div>
					<div>Cache age: {$priceCacheStats.cache_age_minutes} minutes</div>
				</div>
			{:else}
				<div class="text-gray-500">No price cache statistics available</div>
			{/if}

			<div class="mt-3">
				<button
					class="mr-2 rounded bg-red-500 px-3 py-1 text-sm text-white hover:bg-red-600"
					on:click={handleClearPriceCache}
					disabled={clearingPriceCache}
				>
					{clearingPriceCache ? 'Clearing...' : 'Clear Price Cache'}
				</button>
			</div>
		</div>

		<!-- Conversion Cache Stats -->
		<div class="rounded border bg-white p-4">
			<h3 class="mb-2 font-medium">Conversion Cache</h3>
			{#if $conversionCacheStats}
				<div class="text-sm">
					<div>Total entries: {$conversionCacheStats.total_entries}</div>
					<div>Fresh entries: {$conversionCacheStats.fresh_entries}</div>
					<div>Cache age: {$conversionCacheStats.cache_age_hours} hours</div>
				</div>
			{:else}
				<div class="text-gray-500">No conversion cache statistics available</div>
			{/if}

			<div class="mt-3">
				<button
					class="mr-2 rounded bg-red-500 px-3 py-1 text-sm text-white hover:bg-red-600"
					on:click={handleClearConversionCache}
					disabled={clearingConversionCache}
				>
					{clearingConversionCache ? 'Clearing...' : 'Clear Conversion Cache'}
				</button>
			</div>
		</div>
	</div>

	<div class="mb-4">
		<h3 class="mb-2 font-medium">Actions</h3>
		<button
			class="mr-2 rounded bg-blue-500 px-3 py-1 text-white hover:bg-blue-600"
			on:click={handleRefreshAllPrices}
			disabled={refreshing}
		>
			{refreshing ? 'Refreshing...' : 'Refresh All Prices'}
		</button>

		<button
			class="rounded bg-gray-500 px-3 py-1 text-white hover:bg-gray-600"
			on:click={() => refreshAssetCacheStatus()}
			disabled={$cacheRefreshInProgress}
		>
			{$cacheRefreshInProgress ? 'Refreshing...' : 'Refresh Cache Status'}
		</button>
	</div>

	<div>
		<h3 class="mb-2 font-medium">Asset Cache Status</h3>
		<div class="max-h-64 overflow-y-auto">
			<table class="min-w-full bg-white">
				<thead>
					<tr>
						<th
							class="border-b px-3 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
							>Symbol</th
						>
						<th
							class="border-b px-3 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
							>Type</th
						>
						<th
							class="border-b px-3 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
							>Status</th
						>
						<th
							class="border-b px-3 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
							>Cached At</th
						>
						<th
							class="border-b px-3 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
							>Expires</th
						>
					</tr>
				</thead>
				<tbody>
					{#if $assetCacheStatuses.size === 0}
						<tr>
							<td colspan="5" class="px-3 py-2 text-center text-gray-500"
								>No asset cache data available</td
							>
						</tr>
					{:else}
						{#each Array.from($assetCacheStatuses.values()) as status (status.symbol + '_' + status.type)}
							{@const statusType = cacheStatusService.getCacheStatusType(status)}
							{@const statusClass = cacheStatusService.getCacheStatusClass(statusType)}
							<tr>
								<td class="border-b px-3 py-2">{status.symbol}</td>
								<td class="border-b px-3 py-2">{status.type}</td>
								<td class="border-b px-3 py-2">
									<span class={statusClass}>
										{cacheStatusService.getCacheStatusText(statusType)}
									</span>
								</td>
								<td class="border-b px-3 py-2">
									{status.cached_at ? cacheStatusService.formatCacheAge(status.cached_at) : 'N/A'}
								</td>
								<td class="border-b px-3 py-2">
									{status.expires_at
										? cacheStatusService.formatTimeUntilExpiration(status.expires_at)
										: 'N/A'}
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>
	</div>

	<div class="mt-4 text-xs text-gray-500">
		Last cache status update: {formatLastRefresh($lastCacheRefresh)}
	</div>
</div>

<style>
	.cache-management-panel {
		background-color: #f9fafb;
	}
</style>
