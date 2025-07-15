
<script lang="ts">
import ValueCell from '$lib/components/ValueCell.svelte';
import CacheStatusIndicator from '$lib/components/CacheStatusIndicator.svelte';
import ProfitLossCell from '$lib/components/ProfitLossCell.svelte';
import { getAssets, refreshAllPrices, getAssetCacheStatus } from '$lib/services/api';
import type { Asset } from '$lib/types';
import type { RefreshAllResponse, AssetCacheStatus } from '$lib/services/api';
import AddAssetForm from '$lib/components/AddAssetForm.svelte';
import Modal from '$lib/components/Modal.svelte';
import { onMount, onDestroy } from 'svelte';

/** @type {import('./$types').PageData} */
export let data;

let showModal = false;
let assetToEdit: Asset | null = null;
let isRefreshing = false;
let lastRefreshTime: Date | null = null;
let refreshResult: RefreshAllResponse | null = null;
let refreshTrigger = 0;
let cacheStatusMap: Map<number, AssetCacheStatus> = new Map();

// Use loaded data from the load function
let allAssets: Asset[] = data.assets || [];

// Initialize cache status map
$: if (data.cacheStatus && data.cacheStatus.length > 0) {
	const newMap = new Map();
	data.cacheStatus.forEach((status: AssetCacheStatus) => {
		newMap.set(status.asset_id, status);
	});
	cacheStatusMap = newMap;
}

let filterLocation = '';
let filterSymbol = '';
let filterType: 'all' | 'cash' | 'stock' | 'crypto' = 'all';

$: filteredAssets = allAssets.filter((asset) => {
	const locationMatch = !filterLocation || asset.name.toLowerCase().includes(filterLocation.toLowerCase());
	const symbolMatch = !filterSymbol || (asset.symbol && asset.symbol.toLowerCase().includes(filterSymbol.toLowerCase()));
	const typeMatch = filterType === 'all' || asset.type === filterType;
	return locationMatch && symbolMatch && typeMatch;
});

function openAddModal() {
	assetToEdit = null;
	showModal = true;
}

function openEditModal(asset: Asset) {
	assetToEdit = asset;
	showModal = true;
}

function handleSave() {
	showModal = false;
	assetToEdit = null;
	// Reload the page to get fresh data
	location.reload();
}

async function reloadCacheStatus() {
	try {
		const cacheStatuses = await getAssetCacheStatus();
		const newMap = new Map();
		cacheStatuses.forEach(status => {
			newMap.set(status.asset_id, status);
		});
		cacheStatusMap = newMap;
	} catch (error) {
		console.error('Failed to reload cache status:', error);
	}
}

// Periodically reload cache status to keep it current
let cacheStatusInterval: number;
onMount(() => {
	// Set initial last refresh time to now if there are assets
	if (allAssets.length > 0) {
		lastRefreshTime = new Date();
	}
	
	// Reload cache status every 10 seconds to keep indicators current
	cacheStatusInterval = setInterval(reloadCacheStatus, 10000);
});

onDestroy(() => {
	if (cacheStatusInterval) {
		clearInterval(cacheStatusInterval);
	}
});

async function handleRefreshAllPrices() {
	if (isRefreshing) return;
	
	isRefreshing = true;
	refreshResult = null;
	
	try {
		refreshResult = await refreshAllPrices();
		lastRefreshTime = new Date();
		// Trigger re-render of price components by incrementing trigger
		refreshTrigger += 1;
		// Reload cache status after refresh with a small delay to ensure cache is updated
		setTimeout(async () => {
			await reloadCacheStatus();
		}, 1000);
	} catch (error) {
		console.error('Failed to refresh prices:', error);
		alert('Failed to refresh prices. Please try again.');
	} finally {
		isRefreshing = false;
	}
}

function formatLastRefresh(date: Date | null): string {
	if (!date) return 'Never';
	
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / (1000 * 60));
	
	if (diffMins < 1) return 'Just now';
	if (diffMins < 60) return `${diffMins} min ago`;
	
	const diffHours = Math.floor(diffMins / 60);
	if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
	
	return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Initial setup is handled in the main onMount above
</script>


{#if showModal}
	<Modal on:close={() => { showModal = false; assetToEdit = null; }}>
		<AddAssetForm
			asset={assetToEdit}
			on:saved={handleSave}
			on:close={() => { showModal = false; assetToEdit = null; }}
		/>
	</Modal>
{/if}

<div class="bg-background text-text-light min-h-screen p-8">
	<header class="mb-8">
		<h1 class="font-headline text-4xl text-gold">Cointainr</h1>
	</header>

	<section class="bg-surface rounded-lg p-4 mb-8 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<input type="text" bind:value={filterLocation} placeholder="Location/Broker..." class="bg-background text-text-light rounded p-2" />
			<input type="text" bind:value={filterSymbol} placeholder="Symbol/ISIN..." class="bg-background text-text-light rounded p-2" />
			<select bind:value={filterType} class="bg-background text-text-light rounded p-2">
				<option value="all">All Types</option>
				<option value="cash">Cash</option>
				<option value="stock">Stock</option>
				<option value="crypto">Crypto</option>
			</select>
		</div>
		<div class="flex items-center gap-4">
			<button 
				on:click={handleRefreshAllPrices} 
				disabled={isRefreshing}
				class="bg-surface hover:bg-gray-600 disabled:opacity-50 text-white font-bold py-2 px-4 rounded border border-gray-500"
				title="Refresh all asset prices"
			>
				{isRefreshing ? 'Refreshing...' : 'Refresh Prices'}
			</button>
			<button on:click={openAddModal} class="bg-gold hover:opacity-80 text-white font-bold py-2 px-4 rounded">
				Add Asset
			</button>
		</div>
	</section>

	<main class="bg-surface rounded-lg p-6 shadow-lg">
		<h2 class="font-headline text-2xl mb-4">Assets</h2>
		{#if filteredAssets.length > 0}
				<div class="overflow-hidden rounded-lg">
					<table class="w-full font-mono border-collapse border border-gray-600 rounded-table">
						<thead>
							<tr class="bg-background border-b-2 border-gray-600">
<th class="font-bold text-left px-4 py-3 border-r border-gray-600 col-span-2">Location/Broker</th>
<th class="font-bold text-left px-4 py-3 border-r border-gray-600">Asset</th>
<th class="font-bold text-left px-4 py-3 border-r border-gray-600">Type</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600">Current Price</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600">Value</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600">Quantity</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600">Purchase Price</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600">Performance (%)</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600">Yield</th>
<th class="font-bold text-center px-4 py-3">Status</th>
							</tr>
						</thead>
						<tbody>
							{#each filteredAssets as asset (asset.id)}
								<tr
									tabindex="0"
									on:click={() => openEditModal(asset)}
									on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && openEditModal(asset)}
									class="hover:bg-surface cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary border-b border-gray-600 transition-colors"
									aria-label={`Edit asset ${asset.name}`}
								>
									<td class="px-4 py-3 border-r border-gray-600 col-span-2">{asset.name}</td>
<td class="px-4 py-3 border-r border-gray-600">{asset.assetname ?? asset.symbol ?? '-'}</td>
									<td class="px-4 py-3 border-r border-gray-600 capitalize">{asset.type}</td>
									<td class="px-4 py-3 border-r border-gray-600 text-right">
	{#if asset.type === 'cash'}
		-
	{:else if asset.type === 'stock' || asset.type === 'crypto'}
		<ValueCell 
			symbol={asset.symbol ?? ''} 
			quantity={1} 
			currency={asset.buy_currency ?? asset.currency ?? 'USD'} 
			assetType={asset.type}
			refreshTrigger={refreshTrigger}
		/>
	{:else}
		-
	{/if}
</td>
<td class="px-4 py-3 border-r border-gray-600 text-right">
	{#if asset.type === 'cash'}
		{asset.quantity.toFixed(2)} {asset.currency}
	{:else if asset.type === 'stock' || asset.type === 'crypto'}
		<ValueCell 
			symbol={asset.symbol ?? ''} 
			quantity={asset.quantity} 
			currency={asset.buy_currency ?? asset.currency ?? 'USD'} 
			assetType={asset.type}
			refreshTrigger={refreshTrigger}
		/>
	{:else}
		-
	{/if}
</td>
									<td class="px-4 py-3 border-r border-gray-600 text-right">
										{#if asset.type === 'cash'}
											-
										{:else}
											{asset.quantity}
										{/if}
									</td>
									<td class="px-4 py-3 border-r border-gray-600 text-right">
										{#if asset.purchase_price}
											{asset.purchase_price.toFixed(2)} {asset.buy_currency ?? asset.currency ?? ''}
										{:else}
											-
										{/if}
									</td>
									<td class="px-4 py-3 border-r border-gray-600 text-right">
										{#if asset.type === 'cash'}
											-
										{:else if asset.type === 'stock' || asset.type === 'crypto'}
											<ProfitLossCell 
												symbol={asset.symbol ?? ''} 
												quantity={asset.quantity}
												purchasePrice={asset.purchase_price}
												currency={asset.buy_currency ?? asset.currency ?? 'USD'} 
												assetType={asset.type}
												refreshTrigger={refreshTrigger}
												displayType="percentage"
											/>
										{:else}
											-
										{/if}
									</td>
									<td class="px-4 py-3 border-r border-gray-600 text-right">
										{#if asset.type === 'cash'}
											-
										{:else if asset.type === 'stock' || asset.type === 'crypto'}
											<ProfitLossCell 
												symbol={asset.symbol ?? ''} 
												quantity={asset.quantity}
												purchasePrice={asset.purchase_price}
												currency={asset.buy_currency ?? asset.currency ?? 'USD'} 
												assetType={asset.type}
												refreshTrigger={refreshTrigger}
												displayType="absolute"
											/>
										{:else}
											-
										{/if}
									</td>
<td class="px-4 py-3 text-center">
	{#if cacheStatusMap.has(asset.id)}
		{@const cacheStatus = cacheStatusMap.get(asset.id)}
		{#if cacheStatus}
			<CacheStatusIndicator 
				cachedAt={cacheStatus.cached_at}
				cacheTtlMinutes={cacheStatus.cache_ttl_minutes}
				assetType={asset.type}
			/>
		{:else}
			🔴
		{/if}
	{:else}
		🔴
	{/if}
</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-center py-4">No matching assets found.</p>
			{/if}
	</main>
</div>