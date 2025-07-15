
<script lang="ts">
import ValueCell from '$lib/components/ValueCell.svelte';
import CacheStatusIndicator from '$lib/components/CacheStatusIndicator.svelte';
import ProfitLossCell from '$lib/components/ProfitLossCell.svelte';
import { getAssets, refreshAllPrices, getAssetCacheStatus, getStockPrice, getCryptoPrice } from '$lib/services/api';
import type { Asset } from '$lib/types';
import type { RefreshAllResponse, AssetCacheStatus } from '$lib/services/api';
import AddAssetForm from '$lib/components/AddAssetForm.svelte';
import Modal from '$lib/components/Modal.svelte';
import { PriceManagementService } from '$lib/services/priceManagement';
import { PortfolioCalculationService, type PortfolioTotals } from '$lib/services/portfolioCalculations';
import { onMount, onDestroy } from 'svelte';
import { formatCurrency, formatPercentage, formatNumber } from '$lib/utils/numberFormat';

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

// Store current prices for sorting and aggregation
let assetPrices: Map<number, { price: number; currency: string }> = new Map();
let pricesLoaded = false;
let totalCurrency = 'EUR'; // Default currency for totals display

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

// Sorting state
type SortField = 'location' | 'asset' | 'type' | 'currentPrice' | 'value' | 'quantity' | 'purchasePrice' | 'performance' | 'yield';
let sortField: SortField | null = null;
let sortDirection: 'asc' | 'desc' = 'asc';

// Initialize services
const priceManagementService = new PriceManagementService();
let portfolioCalculationService: PortfolioCalculationService;

// Helper function to get current price for an asset
function getCurrentPrice(asset: Asset): number {
	if (asset.type === 'cash') {
		return 1; // Cash has no price, value is just quantity
	}
	return priceManagementService.getCurrentPrice(asset);
}

// Helper function to calculate current value (for sorting)
function getCurrentValue(asset: Asset): number {
	if (asset.type === 'cash') {
		return asset.quantity;
	}
	
	// This is a simplified version for sorting purposes
	// The actual display values are calculated by ValueCell component
	const currentPrice = getCurrentPrice(asset);
	if (currentPrice === 0) {
		return 0;
	}
	
	// Return raw value - conversion is handled in aggregation functions
	return currentPrice * asset.quantity;
}

// Helper function to calculate performance percentage
function getPerformancePercentage(asset: Asset): number {
	if (asset.type === 'cash') {
		return 0;
	}
	
	// Need both purchase price and current price to calculate performance
	if (!asset.purchase_price || asset.purchase_price === 0) {
		return 0;
	}
	
	const currentPrice = getCurrentPrice(asset);
	if (currentPrice === 0) {
		return 0;
	}
	
	return ((currentPrice - asset.purchase_price) / asset.purchase_price) * 100;
}

// Helper function to calculate yield (absolute profit/loss)
function getYield(asset: Asset): number {
	if (asset.type === 'cash' || !asset.purchase_price) {
		return 0;
	}
	const currentPrice = getCurrentPrice(asset);
	return (currentPrice - asset.purchase_price) * asset.quantity;
}

// Sort function
function sortAssets(assets: Asset[], field: SortField | null, direction: 'asc' | 'desc'): Asset[] {
	if (!field) return assets;
	
	return [...assets].sort((a, b) => {
		let aVal: any;
		let bVal: any;
		
		switch (field) {
			case 'location':
				aVal = a.name || '';
				bVal = b.name || '';
				break;
			case 'asset':
				aVal = a.assetname || a.symbol || '';
				bVal = b.assetname || b.symbol || '';
				break;
			case 'type':
				aVal = a.type || '';
				bVal = b.type || '';
				break;
			case 'currentPrice':
				aVal = getCurrentPrice(a);
				bVal = getCurrentPrice(b);
				break;
			case 'value':
				aVal = getCurrentValue(a);
				bVal = getCurrentValue(b);
				break;
			case 'quantity':
				aVal = a.quantity || 0;
				bVal = b.quantity || 0;
				break;
			case 'purchasePrice':
				aVal = a.purchase_price || 0;
				bVal = b.purchase_price || 0;
				break;
			case 'performance':
				aVal = getPerformancePercentage(a);
				bVal = getPerformancePercentage(b);
				// Handle cases where one or both assets have no performance data
				if (isNaN(aVal)) aVal = 0;
				if (isNaN(bVal)) bVal = 0;
				break;
			case 'yield':
				aVal = getYield(a);
				bVal = getYield(b);
				break;
			default:
				return 0;
		}
		
		// Handle string comparison
		if (typeof aVal === 'string' && typeof bVal === 'string') {
			return direction === 'asc' 
				? aVal.localeCompare(bVal)
				: bVal.localeCompare(aVal);
		}
		
		// Handle numeric comparison
		if (direction === 'asc') {
			return aVal - bVal;
		} else {
			return bVal - aVal;
		}
	});
}

// Handle sort click
function handleSort(field: SortField) {
	if (sortField === field) {
		// Same field clicked, toggle direction
		sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
	} else {
		// New field clicked, default to ascending
		sortField = field;
		sortDirection = 'asc';
	}
}

// Function to fetch all current prices for sorting and aggregation
async function fetchAllCurrentPrices() {
	console.log('=== fetchAllCurrentPrices START ===');
	
	try {
		// Use the price management service to fetch all prices
		const pricesMap = await priceManagementService.fetchAllCurrentPrices(allAssets);
		
		// Update the local variables
		assetPrices = pricesMap;
		pricesLoaded = true;
		
		// Initialize the portfolio calculation service with the updated prices
		portfolioCalculationService = new PortfolioCalculationService(assetPrices);
		
		console.log('Updated assetPrices Map:', Array.from(assetPrices.entries()));
		console.log('=== fetchAllCurrentPrices END ===');
	} catch (error) {
		console.error('Failed to fetch current prices:', error);
	}
}

$: filteredAssets = allAssets.filter((asset) => {
	const locationMatch = !filterLocation || asset.name.toLowerCase().includes(filterLocation.toLowerCase());
	const symbolMatch = !filterSymbol || (asset.symbol && asset.symbol.toLowerCase().includes(filterSymbol.toLowerCase()));
	const typeMatch = filterType === 'all' || asset.type === filterType;
	return locationMatch && symbolMatch && typeMatch;
});

$: sortedAssets = sortAssets(filteredAssets, sortField, sortDirection);

// Reactive totals that update when pricesLoaded or totalCurrency changes
let totalValue = 0;
let totalYield = 0;
let totalPerformance = 0;

// Function to update all totals
async function updateTotals() {
	if (!pricesLoaded || !portfolioCalculationService) {
		totalValue = 0;
		totalYield = 0;
		totalPerformance = 0;
		return;
	}
	
	try {
		totalValue = await portfolioCalculationService.calculateTotalValue(sortedAssets, totalCurrency);
		totalYield = await portfolioCalculationService.calculateTotalYield(sortedAssets, totalCurrency);
		totalPerformance = await portfolioCalculationService.calculateTotalPerformance(sortedAssets, totalCurrency);
	} catch (error) {
		console.error('Error updating totals:', error);
	}
}

// Update totals when prices are loaded or currency changes
$: if (pricesLoaded || totalCurrency) {
	updateTotals();
}

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
onMount(async () => {
	// Set initial last refresh time to now if there are assets
	if (allAssets.length > 0) {
		lastRefreshTime = new Date();
		// Fetch initial prices for sorting
		await fetchAllCurrentPrices();
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
		console.log('Refreshing all asset prices...');
		
		// Use the backend refresh-all endpoint
		refreshResult = await refreshAllPrices();
		
		// Then fetch the updated prices for our frontend state
		await fetchAllCurrentPrices();
		
		lastRefreshTime = new Date();
		// Trigger re-render of price components by incrementing trigger
		refreshTrigger += 1;
		
		// Reload cache status after refresh with a small delay to ensure cache is updated
		setTimeout(async () => {
			await reloadCacheStatus();
		}, 1500);
		
		console.log('Price refresh completed successfully:', refreshResult);
		
		// Show success message if there were errors
		if (refreshResult.errors > 0) {
			console.warn(`Refresh completed with ${refreshResult.errors} errors:`, refreshResult.error_details);
		}
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
			<div class="flex items-center gap-2 ml-4 border-l border-gray-600 pl-4">
				<label for="totalCurrency" class="text-text-light text-sm">Totals in:</label>
				<select 
					id="totalCurrency"
					bind:value={totalCurrency}
					class="bg-background text-text-light px-3 py-1 rounded border border-gray-600"
				>
					<option value="EUR">EUR</option>
					<option value="USD">USD</option>
					<option value="GBP">GBP</option>
					<option value="CHF">CHF</option>
				</select>
			</div>
		</div>
		<div class="flex items-center gap-4">
			<button 
				on:click={handleRefreshAllPrices} 
				disabled={isRefreshing}
				class="bg-primary hover:opacity-80 disabled:opacity-50 text-white font-bold p-2 rounded border border-primary disabled:cursor-not-allowed flex items-center justify-center"
				title="Refresh Assetprices"
				aria-label="Refresh Assetprices"
			>
				<svg class="w-5 h-5" class:animate-spin={isRefreshing} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
				</svg>
			</button>
			<button on:click={openAddModal} class="bg-gold hover:opacity-80 text-white font-bold py-2 px-4 rounded">
				Add Asset
			</button>
		</div>
	</section>

	<main class="bg-surface rounded-lg p-6 shadow-lg">
		<h2 class="font-headline text-2xl mb-4">Assets</h2>
		{#if sortedAssets.length > 0}
				<div class="overflow-hidden rounded-lg">
					<table class="w-full font-mono border-collapse border border-gray-600 rounded-table">
						<thead>
							<tr class="bg-background border-b-2 border-gray-600">
<th class="font-bold text-left px-4 py-3 border-r border-gray-600 col-span-2 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('location')}>
	<div class="flex items-center justify-between">
		Location/Broker
		{#if sortField === 'location'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-left px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('asset')}>
	<div class="flex items-center justify-between">
		Asset
		{#if sortField === 'asset'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-left px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('type')}>
	<div class="flex items-center justify-between">
		Type
		{#if sortField === 'type'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('currentPrice')}>
	<div class="flex items-center justify-end">
		Current Price
		{#if sortField === 'currentPrice'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('value')}>
	<div class="flex items-center justify-end">
		Value
		{#if sortField === 'value'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('quantity')}>
	<div class="flex items-center justify-end">
		Quantity
		{#if sortField === 'quantity'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('purchasePrice')}>
	<div class="flex items-center justify-end">
		Purchase Price
		{#if sortField === 'purchasePrice'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('performance')}>
	<div class="flex items-center justify-end">
		Performance
		{#if sortField === 'performance'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-right px-4 py-3 border-r border-gray-600 cursor-pointer hover:bg-surface transition-colors" on:click={() => handleSort('yield')}>
	<div class="flex items-center justify-end">
		Yield
		{#if sortField === 'yield'}
			<span class="ml-2 text-primary">
				{sortDirection === 'asc' ? '↑' : '↓'}
			</span>
		{:else}
			<span class="ml-2 text-gray-500">↕</span>
		{/if}
	</div>
</th>
<th class="font-bold text-center px-4 py-3">Status</th>
							</tr>
						</thead>
						<tbody>
							{#each sortedAssets as asset (asset.id)}
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
		{formatCurrency(asset.quantity, asset.currency ?? 'EUR')}
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
											{formatNumber(asset.quantity)}
										{/if}
									</td>
									<td class="px-4 py-3 border-r border-gray-600 text-right">
										{#if asset.purchase_price}
											{formatCurrency(asset.purchase_price, asset.buy_currency ?? asset.currency ?? '')}
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
						<tfoot>
							<tr class="bg-background border-t-2 border-gold font-bold">
								<td class="px-4 py-3 border-r border-gray-600" colspan="2">
									<span class="text-gold">TOTAL ({sortedAssets.length} assets)</span>
								</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-right text-gold font-bold text-lg">
									{formatCurrency(totalValue, totalCurrency)}
								</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-right">
									<span class={totalPerformance >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}>
										{formatPercentage(totalPerformance)}
									</span>
								</td>
								<td class="px-4 py-3 border-r border-gray-600 text-right">
									<span class={totalYield >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}>
										{formatCurrency(totalYield, totalCurrency)}
									</span>
								</td>
								<td class="px-4 py-3 text-center">-</td>
							</tr>
						</tfoot>
					</table>
				</div>
			{:else}
				<p class="text-center py-4">No matching assets found.</p>
			{/if}
	</main>
</div>