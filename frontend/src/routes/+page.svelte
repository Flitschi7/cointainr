
<script lang="ts">
import ValueCell from '$lib/components/ValueCell.svelte';
import CacheStatusIndicator from '$lib/components/CacheStatusIndicator.svelte';
import ProfitLossCell from '$lib/components/ProfitLossCell.svelte';
import { getAssets, refreshAllPrices, getAssetCacheStatus, getStockPrice, getCryptoPrice } from '$lib/services/api';
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

// Helper function to get current price for an asset
function getCurrentPrice(asset: Asset): number {
	if (asset.type === 'cash') {
		return 1; // Cash has no price, value is just quantity
	}
	const priceData = assetPrices.get(asset.id);
	console.log(`getCurrentPrice debug - Asset ID: ${asset.id}, Symbol: ${asset.symbol}, Price data:`, priceData, `Price: ${priceData?.price || 0}`);
	return priceData?.price || 0;
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
	console.log('allAssets:', allAssets);
	console.log('Non-cash assets to fetch prices for:', allAssets.filter(asset => asset.type !== 'cash'));
	
	try {
		const pricePromises = allAssets
			.filter(asset => asset.type !== 'cash') // Skip cash assets
			.map(async (asset) => {
				console.log(`Fetching price for asset: ${asset.symbol}, type: ${asset.type}`);
				try {
					let priceData;
					// Use the same API functions that ValueCell uses
					if (asset.type === 'crypto') {
						priceData = await getCryptoPrice(asset.symbol || '', false);
					} else if (asset.type === 'stock') {
						priceData = await getStockPrice(asset.symbol || '', false);
					}
					
					console.log(`Price data for ${asset.symbol}:`, priceData);
					
					if (priceData) {
						return {
							assetId: asset.id,
							price: priceData.price || 0,
							currency: priceData.currency || 'USD'
						};
					}
				} catch (error) {
					console.error(`Failed to fetch price for ${asset.symbol}:`, error);
				}
				return {
					assetId: asset.id,
					price: 0,
					currency: 'USD'
				};
			});

		const prices = await Promise.all(pricePromises);
		console.log('All fetched prices:', prices);
		
		// Update the assetPrices map
		const newPricesMap = new Map();
		prices.forEach(({ assetId, price, currency }) => {
			newPricesMap.set(assetId, { price, currency });
		});
		
		assetPrices = newPricesMap;
		pricesLoaded = true;
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
	if (!pricesLoaded) {
		totalValue = 0;
		totalYield = 0;
		totalPerformance = 0;
		return;
	}
	
	try {
		totalValue = await calculateTotalValue();
		totalYield = await calculateTotalYield();
		totalPerformance = await calculateTotalPerformance();
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
		refreshResult = await refreshAllPrices();
		lastRefreshTime = new Date();
		// Trigger re-render of price components by incrementing trigger
		refreshTrigger += 1;
		// Fetch updated prices for sorting
		await fetchAllCurrentPrices();
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

// Aggregation functions for summary row - only calculate when prices are loaded
async function calculateTotalValue(): Promise<number> {
	if (!pricesLoaded) {
		console.log('Prices not loaded yet, skipping total calculation');
		return 0;
	}
	
	console.log('=== assetPrices Map contents ===');
	console.log('assetPrices Map size:', assetPrices.size);
	console.log('assetPrices Map entries:', Array.from(assetPrices.entries()));
	console.log('=== end assetPrices Map contents ===');
	
	const { convertCurrency } = await import('$lib/services/api');
	let total = 0;
	
	for (const asset of sortedAssets) {
		let value = 0;
		
		if (asset.type === 'cash') {
			// Cash - assume it's already in EUR, convert if needed
			value = asset.quantity;
			if (totalCurrency !== 'EUR') {
				const conversion = await convertCurrency('EUR', totalCurrency, value, false);
				value = conversion.converted;
			}
		} else {
			const currentPrice = getCurrentPrice(asset);
			if (currentPrice > 0) {
				const rawValue = currentPrice * asset.quantity;
				
				// Get the currency of the price and convert to selected total currency
				const priceData = assetPrices.get(asset.id);
				const priceCurrency = priceData?.currency || 'USD';
				
				if (priceCurrency !== totalCurrency) {
					const conversion = await convertCurrency(priceCurrency, totalCurrency, rawValue, false);
					value = conversion.converted;
				} else {
					value = rawValue;
				}
			}
		}
		
		console.log(`Value calc - Asset: ${asset.symbol || asset.name}, Type: ${asset.type}, CurrentPrice: ${getCurrentPrice(asset)}, Quantity: ${asset.quantity}, Value in ${totalCurrency}: ${value.toFixed(2)}`);
		total += value;
	}
	
	console.log(`Total Value in ${totalCurrency}: ${total.toFixed(2)}`);
	return total;
}

async function calculateTotalYield(): Promise<number> {
	if (!pricesLoaded) {
		return 0;
	}
	
	const { convertCurrency } = await import('$lib/services/api');
	let total = 0;
	
	for (const asset of sortedAssets) {
		let yield_ = 0;
		
		if (asset.type === 'cash') {
			yield_ = 0; // Cash has no yield
		} else {
			const currentPrice = getCurrentPrice(asset);
			const purchasePrice = asset.purchase_price;
			
			if (currentPrice > 0 && purchasePrice && purchasePrice > 0) {
				const currentValue = currentPrice * asset.quantity;
				const investmentValue = purchasePrice * asset.quantity;
				let yieldValue = currentValue - investmentValue;
				
				// Convert to selected total currency
				const priceData = assetPrices.get(asset.id);
				const priceCurrency = priceData?.currency || 'USD';
				
				if (priceCurrency !== totalCurrency) {
					const conversion = await convertCurrency(priceCurrency, totalCurrency, yieldValue, false);
					yieldValue = conversion.converted;
				}
				
				yield_ = yieldValue;
			}
		}
		
		console.log(`Yield calc - Asset: ${asset.symbol || asset.name}, Type: ${asset.type}, CurrentPrice: ${getCurrentPrice(asset)}, PurchasePrice: ${asset.purchase_price}, Quantity: ${asset.quantity}, Yield in ${totalCurrency}: ${yield_.toFixed(2)}`);
		total += yield_;
	}
	
	console.log(`Total Yield in ${totalCurrency}: ${total.toFixed(2)}`);
	return total;
}

async function calculateTotalPerformance(): Promise<number> {
	if (!pricesLoaded) {
		return 0;
	}
	
	// Calculate total current value and total investment
	let totalCurrentValue = 0;
	let totalInvestment = 0;
	
	const { convertCurrency } = await import('$lib/services/api');
	
	for (const asset of sortedAssets) {
		if (asset.type === 'cash') {
			// Cash doesn't contribute to performance calculation
			continue;
		}
		
		const currentPrice = getCurrentPrice(asset);
		const purchasePrice = asset.purchase_price;
		
		if (currentPrice > 0 && purchasePrice && purchasePrice > 0) {
			let currentValue = currentPrice * asset.quantity;
			let investmentValue = purchasePrice * asset.quantity;
			
			// Convert both values to the selected total currency
			const priceData = assetPrices.get(asset.id);
			const priceCurrency = priceData?.currency || 'USD';
			
			if (priceCurrency !== totalCurrency) {
				const currentConversion = await convertCurrency(priceCurrency, totalCurrency, currentValue, false);
				currentValue = currentConversion.converted;
			}
			
			// For investment value, assume same currency as current price for simplicity
			// (In reality, you might want to store the original purchase currency)
			if (priceCurrency !== totalCurrency) {
				const investmentConversion = await convertCurrency(priceCurrency, totalCurrency, investmentValue, false);
				investmentValue = investmentConversion.converted;
			}
			
			totalCurrentValue += currentValue;
			totalInvestment += investmentValue;
			
			console.log(`Performance calc - Asset: ${asset.symbol}, Current Value: ${currentValue.toFixed(2)} ${totalCurrency}, Investment: ${investmentValue.toFixed(2)} ${totalCurrency}`);
		}
	}
	
	if (totalInvestment === 0) {
		console.log(`Total Performance: 0% (no investments)`);
		return 0;
	}
	
	const performancePercent = ((totalCurrentValue - totalInvestment) / totalInvestment) * 100;
	console.log(`Total Performance: ${performancePercent.toFixed(2)}% (Current: ${totalCurrentValue.toFixed(2)} ${totalCurrency}, Investment: ${totalInvestment.toFixed(2)} ${totalCurrency})`);
	return performancePercent;
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
				disabled={true}
				class="bg-gray-500 opacity-50 text-white font-bold py-2 px-4 rounded border border-gray-500 cursor-not-allowed"
				title="Refresh all asset prices (temporarily disabled)"
			>
				Refresh Prices (Disabled)
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
		Performance (%)
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
						<tfoot>
							<tr class="bg-background border-t-2 border-gold font-bold">
								<td class="px-4 py-3 border-r border-gray-600" colspan="2">
									<span class="text-gold">TOTAL ({sortedAssets.length} assets)</span>
								</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-right text-gold font-bold text-lg">
									{totalValue.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {totalCurrency}
								</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-center">-</td>
								<td class="px-4 py-3 border-r border-gray-600 text-right">
									<span class={totalPerformance >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}>
										{totalPerformance >= 0 ? '+' : ''}{totalPerformance.toFixed(2)}%
									</span>
								</td>
								<td class="px-4 py-3 border-r border-gray-600 text-right">
									<span class={totalYield >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}>
										{totalYield >= 0 ? '+' : ''}{totalYield.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {totalCurrency}
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