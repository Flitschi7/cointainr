<script lang="ts">
	import CacheStatusIndicator from '$lib/components/CacheStatusIndicator.svelte';
	import CacheStatusBanner from '$lib/components/CacheStatusBanner.svelte';
	import CurrencyRateDisplay from '$lib/components/CurrencyRateDisplay.svelte';
	import AssetTypePieChart from '$lib/components/AssetTypePieChart.svelte';
	import BrokerPieChart from '$lib/components/BrokerPieChart.svelte';
	import TopHoldings from '$lib/components/TopHoldings.svelte';
	import AssetPerformanceChart from '$lib/components/AssetPerformanceChart.svelte';
	import PortfolioRiskScore from '$lib/components/PortfolioRiskScore.svelte';
	import PortfolioEfficiency from '$lib/components/PortfolioEfficiency.svelte';
	import * as enhancedApi from '$lib/services/enhancedApi';
	import type { Asset } from '$lib/types';
	import type { RefreshAllResponse, AssetCacheStatus } from '$lib/types';
	import { refreshAssetCacheStatus } from '$lib/stores/assetStatusStore';
	import { getContext } from 'svelte';
	import AddAssetForm from '$lib/components/AddAssetForm.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { PriceManagementService } from '$lib/services/priceManagement';
	import {
		PortfolioCalculationService,
		sortValuedAssets,
		type PortfolioSortField,
		type PositionValuation
	} from '$lib/services/portfolioCalculations';
	import { onMount, onDestroy } from 'svelte';
	import { formatCurrency, formatPercentage, formatNumber } from '$lib/utils/numberFormat';
	import { debounce } from 'lodash-es';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import LogoutButton from '$lib/components/LogoutButton.svelte';

	// Conditional logging - only in development
	const isDev = import.meta.env.DEV;
	const log = isDev ? console.log : () => {};

	/** @type {import('./$types').PageData} */
	export let data;

	let showModal = false;
	let assetToEdit: Asset | null = null;
	let isRefreshing = false;
	let lastRefreshTime: Date | null = null;
	let refreshResult: RefreshAllResponse | null = null;
	let refreshTrigger = 0;
	let cacheStatusMap: Map<number, AssetCacheStatus> = new Map();

	// Tab navigation state - derived from URL parameters
	let activeTab: 'portfolio' | 'distribution' | 'analytics' = 'portfolio';

	// Tab definitions
	const tabs = [
		{ id: 'portfolio', label: 'Portfolio', icon: '📈' },
		{ id: 'distribution', label: 'Distribution', icon: '📊' },
		{ id: 'analytics', label: 'Analytics', icon: '🧠' }
	] as const;

	// Update activeTab based on URL parameters
	$: {
		const tabParam = $page.url.searchParams.get('tab');
		if (tabParam === 'distribution') {
			activeTab = 'distribution';
		} else if (tabParam === 'analytics') {
			activeTab = 'analytics';
		} else {
			activeTab = 'portfolio';
		}
	}

	function setActiveTab(tabId: 'portfolio' | 'distribution' | 'analytics') {
		// Update URL without page reload
		const url = new URL($page.url);
		if (tabId === 'portfolio') {
			url.searchParams.delete('tab'); // Default tab, no need for parameter
		} else {
			url.searchParams.set('tab', tabId);
		}
		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	// Get cache status from context (provided by CacheStatusProvider)
	const cacheContext = getContext('cacheStatus') as { assetCacheStatus: any } | undefined;

	// Extract the store from context at the top level
	let contextAssetCacheStatus: any = null;
	if (cacheContext) {
		contextAssetCacheStatus = cacheContext.assetCacheStatus;
	}

	// Use loaded data from the load function
	let allAssets: Asset[] = data.assets || [];

	// Store current prices for sorting and aggregation
	// Initialize with any prices loaded during page load
	let assetPrices: Map<number, { price: number; currency: string }> = new Map();
	let pricesLoaded = false;
	let totalCurrency = 'EUR'; // Default currency for totals display

	// Initialize assetPrices with any initial prices loaded during page load
	if (data.initialPrices) {
		// Convert from object back to Map
		Object.entries(data.initialPrices).forEach(([key, value]) => {
			const assetId = parseInt(key, 10);
			if (!isNaN(assetId) && value && typeof value === 'object') {
				// Type check to ensure value has price and currency properties
				const priceValue = 'price' in value ? (value.price as number) : NaN;
				const currencyValue = 'currency' in value ? (value.currency as string) : '';
				if (
					!Number.isFinite(priceValue) ||
					priceValue < 0 ||
					!currencyValue ||
					('source' in value && value.source === 'error')
				)
					return;

				assetPrices.set(assetId, {
					price: priceValue,
					currency: currencyValue
				});
			}
		});

		// If we have initial prices, consider them loaded
		pricesLoaded = assetPrices.size > 0;

		if (pricesLoaded) {
			const cacheInfo = data.cacheMetadata;
			// Only log in development mode
			if (isDev) {
				log(
					`Using ${assetPrices.size} prices from initial page load (${cacheInfo?.cacheHits || 0} from cache, ${cacheInfo?.apiCalls || 0} from API, ${cacheInfo?.cacheEfficiency?.toFixed(1) || 0}% cache efficiency)`
				);
			}
		}
	}

	// Initialize cache status map from context store
	$: if (
		contextAssetCacheStatus &&
		$contextAssetCacheStatus &&
		$contextAssetCacheStatus.length > 0
	) {
		const newMap = new Map();
		$contextAssetCacheStatus.forEach((status: AssetCacheStatus) => {
			newMap.set(status.asset_id, status);
		});
		cacheStatusMap = newMap;
	} else if (data.cacheStatus && data.cacheStatus.length > 0) {
		// Fallback to initial data if context is not available
		const newMap = new Map();
		data.cacheStatus.forEach((status: AssetCacheStatus) => {
			newMap.set(status.asset_id, status);
		});
		cacheStatusMap = newMap;
	}

	let filterLocation = '';
	let filterSymbol = '';
	let filterType: 'all' | 'cash' | 'stock' | 'crypto' | 'derivative' = 'all';

	// Sorting state
	type SortField = PortfolioSortField;
	let sortField: SortField | null = null;
	let sortDirection: 'asc' | 'desc' = 'asc';
	const sortColumns: { field: SortField; label: string; numeric: boolean }[] = [
		{ field: 'location', label: 'Location/Broker', numeric: false },
		{ field: 'type', label: 'Type', numeric: false },
		{ field: 'asset', label: 'Asset', numeric: false },
		{ field: 'quantity', label: 'Quantity', numeric: true },
		{ field: 'purchasePrice', label: 'Purchase Price', numeric: true },
		{ field: 'currentPrice', label: 'Current Price', numeric: true },
		{ field: 'value', label: 'Value', numeric: true },
		{ field: 'yield', label: 'Yield', numeric: true },
		{ field: 'performance', label: 'Performance', numeric: true }
	];

	// Initialize services
	const priceManagementService = new PriceManagementService();

	// Initialize the price management service with loaded prices
	$: if (assetPrices.size > 0 && !priceManagementService.isPricesLoaded()) {
		// Set the prices in the service
		priceManagementService.setPrices(assetPrices);
		if (isDev) {
			log(`Initialized PriceManagementService with ${assetPrices.size} prices`);
		}
	}

	const debouncedFilterUpdate = debounce(() => {
		filteredAssets = allAssets.filter((asset) => {
			const locationMatch =
				!filterLocation || asset.name.toLowerCase().includes(filterLocation.toLowerCase());
			const symbolMatch =
				!filterSymbol ||
				(asset.symbol && asset.symbol.toLowerCase().includes(filterSymbol.toLowerCase()));
			const typeMatch = filterType === 'all' || asset.type === filterType;
			return locationMatch && symbolMatch && typeMatch;
		});
	}, 300);

	// Function to fetch all current prices for sorting and aggregation
	async function fetchAllCurrentPrices(forceRefresh = false) {
		void (isDev && log(`=== fetchAllCurrentPrices START (forceRefresh: ${forceRefresh}) ===`));

		try {
			// If we already have prices loaded from the page data and we're not forcing refresh,
			// we can skip the API calls and use what we have
			if (pricesLoaded && !forceRefresh && assetPrices.size > 0) {
				void (isDev && log('Using prices already loaded from page data (skipping API calls)'));
				return;
			}

			// Use the price management service to fetch all prices
			// Pass the forceRefresh parameter to respect cache when appropriate
			const pricesMap = await priceManagementService.fetchAllCurrentPrices(allAssets, forceRefresh);

			// Update the local variables
			assetPrices = pricesMap;
			pricesLoaded = true;

			void (isDev && log('Updated assetPrices Map:', Array.from(assetPrices.entries())));
			void (isDev && log('=== fetchAllCurrentPrices END ==='));
		} catch (error) {
			console.error('Failed to fetch current prices:', error);

			// Provide more detailed error information
			const errorMessage = error instanceof Error ? error.message : String(error);
			const errorSource = errorMessage.includes('network')
				? 'Network error'
				: errorMessage.includes('timeout')
					? 'API timeout'
					: 'API error';

			// If we already have some prices loaded, we can continue using them
			if (assetPrices.size > 0) {
				console.warn(`Using existing cached prices due to ${errorSource}: ${errorMessage}`);
				pricesLoaded = true;
			} else {
				// No prices available, show a warning
				console.warn(`No prices available due to ${errorSource}: ${errorMessage}`);
			}
		}
	}

	// Initialize filtered assets from initial data
	let filteredAssets: Asset[] = allAssets;

	// Reactive statement for filter changes - debounced
	$: {
		// Trigger debounced update when filters change
		(filterLocation, filterSymbol, filterType, allAssets);
		debouncedFilterUpdate();
	}

	let sortedAssets: Asset[] = [];

	// Updated sort handler that triggers immediate update
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

	let totalValue: number | null = null;
	let totalYield: number | null = null;
	let totalPerformance: number | null = null;
	let isCalculatingTotals = false;
	let totalsRevision = 0;
	let positionValuations = new Map<number, PositionValuation>();

	async function updateValuation(
		assets: Asset[],
		currency: string,
		prices: Map<number, { price: number; currency: string }>,
		ready: boolean
	) {
		const revision = ++totalsRevision;
		totalValue = null;
		totalYield = null;
		totalPerformance = null;
		positionValuations = new Map();
		isCalculatingTotals = assets.length > 0;
		if (!ready) return;
		const calculator = new PortfolioCalculationService(new Map(prices));
		try {
			const valuation = await calculator.calculatePortfolioValuation(
				assets.map((asset) => ({ ...asset })),
				currency
			);
			if (revision !== totalsRevision) return;
			positionValuations = valuation.positions;
			totalValue = valuation.totals.totalValue;
			totalYield = valuation.totals.totalYield;
			totalPerformance = valuation.totals.totalPerformance;
		} catch (error) {
			if (revision !== totalsRevision) return;
			console.error('Error calculating totals:', error);
		} finally {
			if (revision === totalsRevision) isCalculatingTotals = false;
		}
	}

	$: updateValuation(filteredAssets, totalCurrency, assetPrices, pricesLoaded);
	$: sortedAssets = sortValuedAssets(filteredAssets, positionValuations, sortField, sortDirection);

	function formatValuation(value: number | null | undefined, percentage = false): string {
		if (value == null) return isCalculatingTotals ? '...' : 'Unavailable';
		return percentage ? formatPercentage(value) : formatCurrency(value, totalCurrency);
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
			// Use the centralized cache store refresh function
			await refreshAssetCacheStatus();
		} catch (error) {
			console.error('Failed to reload cache status:', error);
		}
	}

	// Periodically reload cache status to keep it current
	let cacheStatusInterval: ReturnType<typeof setInterval> | null = null;
	// Set up adaptive cache polling based on cache health
	const setupAdaptiveCachePolling = () => {
		// Get current cache health from metadata
		const cacheEfficiency = cacheMetadata?.cacheEfficiency || 100;

		// Determine polling interval based on cache health:
		// - High efficiency (>80%): Poll every 60 seconds
		// - Medium efficiency (50-80%): Poll every 30 seconds
		// - Low efficiency (<50%): Poll every 15 seconds
		const pollingInterval = cacheEfficiency > 80 ? 60000 : cacheEfficiency > 50 ? 30000 : 15000;

		console.debug(
			`Setting cache polling interval to ${pollingInterval / 1000} seconds (cache efficiency: ${cacheEfficiency.toFixed(1)}%)`
		);

		// Clear existing interval if any
		if (cacheStatusInterval) {
			clearInterval(cacheStatusInterval);
		}

		// Set new interval
		cacheStatusInterval = setInterval(reloadCacheStatus, pollingInterval);
	};

	onMount(async () => {
		// Set initial last refresh time based on cache metadata if available
		if (cacheMetadata && cacheMetadata.loadedAt) {
			lastRefreshTime = new Date(cacheMetadata.loadedAt);
		} else if (allAssets.length > 0) {
			lastRefreshTime = new Date();
		}

		// Use cache-first approach on page load
		if (allAssets.length > 0) {
			isDev && log('Fetching all prices on page load with cache-first approach');
			// Don't force refresh, use cache-first approach
			await fetchAllCurrentPrices(false);
		}

		// Set up the adaptive cache polling
		setupAdaptiveCachePolling();

		// Initialize the cache status
		await enhancedApi.getFrontendCacheStats();
	});

	onDestroy(() => {
		totalsRevision += 1;
		debouncedFilterUpdate.cancel();
		if (cacheStatusInterval) {
			clearInterval(cacheStatusInterval);
		}
	});

	async function handleRefreshAllPrices() {
		if (isRefreshing) return;

		isRefreshing = true;
		refreshResult = null;

		try {
			isDev && log('Manually refreshing all asset prices (bypassing cache)...');

			// Use the enhanced API to refresh all prices
			refreshResult = await enhancedApi.refreshAllPrices();

			// Then fetch the updated prices for our frontend state
			// Explicitly force refresh to bypass cache completely
			await fetchAllCurrentPrices(true);

			lastRefreshTime = new Date();
			// Trigger re-render of price components by incrementing trigger
			refreshTrigger += 1;

			// Reload cache status after refresh with a small delay to ensure cache is updated
			setTimeout(async () => {
				await reloadCacheStatus();
				// Also update frontend cache stats
				await enhancedApi.getFrontendCacheStats();
				// Force update the asset prices display by triggering reactivity
				assetPrices = new Map(assetPrices);
			}, 1500);

			isDev && log('Manual price refresh completed successfully:', refreshResult);

			// Show success message if there were errors
			if (refreshResult.errors > 0) {
				console.warn(
					`Refresh completed with ${refreshResult.errors} errors:`,
					refreshResult.error_details
				);
			}
		} catch (error) {
			console.error('Failed to refresh prices:', error);

			// Provide more detailed error information
			const errorMessage = error instanceof Error ? error.message : String(error);
			const errorSource = errorMessage.includes('network')
				? 'Network error'
				: errorMessage.includes('timeout')
					? 'API timeout'
					: 'API error';

			// Show a more informative error message
			alert(
				`Failed to refresh prices: ${errorSource}. ${errorMessage}\n\nThe system will continue using cached data where available.`
			);

			// Even if refresh fails, try to reload cache status to show what's still valid
			try {
				await reloadCacheStatus();
			} catch (cacheError) {
				console.error('Failed to reload cache status after refresh error:', cacheError);
			}
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

		return (
			date.toLocaleDateString() +
			' ' +
			date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
		);
	}

	// Check if we're using cached data from the page load
	$: cacheMetadata = data.cacheMetadata || { loadedAt: null, usedCache: false };

	// Initial setup is handled in the main onMount above
</script>

{#if showModal}
	<Modal
		on:close={() => {
			showModal = false;
			assetToEdit = null;
		}}
	>
		<AddAssetForm
			asset={assetToEdit}
			on:saved={handleSave}
			on:close={() => {
				showModal = false;
				assetToEdit = null;
			}}
		/>
	</Modal>
{/if}

<div class="bg-background text-text-light min-h-screen overflow-x-hidden p-4 sm:p-6 lg:p-8">
	<header class="mb-6 sm:mb-8">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<h1 class="font-headline text-gold text-2xl sm:text-3xl lg:text-4xl">Cointainr</h1>

			<div class="flex flex-col gap-4 sm:flex-row sm:items-center">
				<!-- Tab Navigation -->
				<nav class="flex-shrink-0">
					<div class="bg-surface rounded-lg p-1">
						<div class="flex space-x-1">
							{#each tabs as tab}
								<button
									class="flex cursor-pointer items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-all duration-200 {activeTab ===
									tab.id
										? 'bg-background text-text-light border border-gray-600'
										: 'hover:text-text-light hover:bg-background/50 text-gray-400'}"
									on:click={() => setActiveTab(tab.id)}
								>
									<span class="text-base">{tab.icon}</span>
									<span class="hidden sm:inline">{tab.label}</span>
								</button>
							{/each}
						</div>
					</div>
				</nav>

				<!-- Logout Button (only show if authentication is enabled) -->
				{#if data.user}
					<LogoutButton />
				{/if}
			</div>
		</div>
	</header>

	<!-- Filters Section -->
	<section class="bg-surface mb-6 rounded-lg p-4 sm:mb-8">
		<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
			<div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
				<input
					type="text"
					bind:value={filterLocation}
					placeholder="Filter by location or broker..."
					class="bg-surface text-text-light focus:border-primary focus:ring-primary w-full rounded-lg border border-gray-600 px-3 py-2 text-sm placeholder-gray-400 focus:ring-1 focus:outline-none sm:w-auto"
				/>
				<input
					type="text"
					bind:value={filterSymbol}
					placeholder="Filter by symbol or ISIN..."
					class="bg-surface text-text-light focus:border-primary focus:ring-primary w-full rounded-lg border border-gray-600 px-3 py-2 text-sm placeholder-gray-400 focus:ring-1 focus:outline-none sm:w-auto"
				/>
				<select
					bind:value={filterType}
					class="bg-surface text-text-light focus:border-primary focus:ring-primary w-full rounded-lg border border-gray-600 px-3 py-2 text-sm focus:ring-1 focus:outline-none sm:w-auto"
				>
					<option value="all">All asset types</option>
					<option value="cash">Cash</option>
					<option value="stock">Stocks</option>
					<option value="crypto">Cryptocurrency</option>
					<option value="derivative">Derivatives</option>
				</select>
				<div class="flex items-center gap-3 border-l border-gray-600 pl-4">
					<label for="totalCurrency" class="text-text-light text-sm font-medium whitespace-nowrap">
						Display currency:
					</label>
					<select
						id="totalCurrency"
						bind:value={totalCurrency}
						class="bg-surface text-text-light focus:border-primary focus:ring-primary rounded-lg border border-gray-600 px-3 py-2 text-sm focus:ring-1 focus:outline-none"
					>
						<option value="EUR">EUR (€)</option>
						<option value="USD">USD ($)</option>
						<option value="GBP">GBP (£)</option>
						<option value="CHF">CHF</option>
					</select>
					<CurrencyRateDisplay baseCurrency={totalCurrency} assets={allAssets} />
				</div>
			</div>
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
				<!-- Cache status is now handled by CacheStatusBanner component -->
				<button
					on:click={handleRefreshAllPrices}
					disabled={isRefreshing}
					class="bg-primary focus:ring-primary hover:bg-opacity-90 focus:ring-opacity-50 flex cursor-pointer items-center justify-center gap-2 rounded-lg px-4 py-2 font-semibold text-white transition-all duration-200 hover:shadow-lg focus:ring-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
					title="Force refresh all prices (bypass cache)"
					aria-label="Force refresh all prices"
				>
					<svg
						class="h-4 w-4"
						class:animate-spin={isRefreshing}
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						></path>
					</svg>
					<span>Force Refresh</span>
				</button>
				<button
					on:click={openAddModal}
					class="bg-gold focus:ring-gold hover:bg-opacity-90 focus:ring-opacity-50 flex cursor-pointer items-center justify-center gap-2 rounded-lg px-4 py-2 font-semibold text-white transition-all duration-200 hover:shadow-lg focus:ring-2 focus:outline-none sm:w-auto"
				>
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"
						></path>
					</svg>
					Add Asset
				</button>
			</div>
		</div>
	</section>

	<!-- Tab Content -->
	{#if activeTab === 'portfolio'}
		<!-- Portfolio Tab Content -->
		<main class="bg-surface rounded-lg p-4 shadow-lg sm:p-6">
			<div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
				<h2 class="font-headline text-xl sm:text-2xl">Assets</h2>
				<div class="text-sm text-gray-400">
					Last refresh: {formatLastRefresh(lastRefreshTime)}
				</div>
			</div>

			<!-- No need for additional refresh button as we have Force Refresh in the nav bar -->
			{#if sortedAssets.length > 0}
				<div class="overflow-x-auto rounded-lg">
					<table
						class="rounded-table table-responsive w-full min-w-[800px] border-collapse border border-gray-600 font-mono text-sm"
					>
						<thead>
							<tr class="bg-background border-b-2 border-gray-600">
								{#each sortColumns as column (column.field)}
									<th
										class="hover:bg-surface border-r border-gray-600 px-2 py-2 font-bold transition-colors sm:px-4 sm:py-3"
										aria-sort={sortField === column.field
											? sortDirection === 'asc'
												? 'ascending'
												: 'descending'
											: undefined}
									>
										<button
											type="button"
											class="focus-visible:ring-primary flex w-full cursor-pointer items-center gap-2 rounded-sm focus-visible:ring-2 focus-visible:outline-none"
											class:justify-end={column.numeric}
											class:justify-between={!column.numeric}
											on:click={() => handleSort(column.field)}
										>
											{column.label}
											<span
												aria-hidden="true"
												class={sortField === column.field ? 'text-primary' : 'text-gray-500'}
											>
												{sortField === column.field ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
											</span>
										</button>
									</th>
								{/each}
								<th class="px-2 py-2 text-center font-bold sm:px-4 sm:py-3">Status</th>
							</tr>
						</thead>
						<tbody>
							{#each sortedAssets as asset (asset.id)}
								{@const valuation = positionValuations.get(asset.id)}
								<tr
									tabindex="0"
									on:click={() => openEditModal(asset)}
									on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && openEditModal(asset)}
									class="hover:bg-background focus:ring-primary cursor-pointer border-b border-gray-600 transition-all duration-200 hover:shadow-sm focus:ring-2 focus:outline-none"
									aria-label={`Edit asset ${asset.name}`}
								>
									<!-- 1. Location/Broker -->
									<td class="col-span-2 border-r border-gray-600 px-2 py-2 sm:px-4 sm:py-3"
										>{asset.name}</td
									>

									<!-- 2. Type -->
									<td class="border-r border-gray-600 px-2 py-2 capitalize sm:px-4 sm:py-3"
										>{asset.type}</td
									>

									<!-- 3. Asset -->
									<td class="border-r border-gray-600 px-2 py-2 sm:px-4 sm:py-3"
										>{asset.assetname ?? asset.symbol ?? '-'}</td
									>

									<!-- 4. Quantity -->
									<td class="border-r border-gray-600 px-2 py-2 text-right sm:px-4 sm:py-3">
										{#if asset.type === 'cash'}
											-
										{:else}
											{formatNumber(asset.quantity)}
										{/if}
									</td>

									<!-- 5. Purchase Price -->
									<td class="border-r border-gray-600 px-2 py-2 text-right sm:px-4 sm:py-3">
										{#if asset.type === 'cash'}
											-
										{:else}
											<span
												title={asset.purchase_price !== null &&
												(asset.buy_currency || asset.currency)
													? `Original: ${formatCurrency(asset.purchase_price, asset.buy_currency || asset.currency || '')}`
													: undefined}
											>
												{formatValuation(valuation?.purchasePrice)}
											</span>
										{/if}
									</td>

									<!-- 6. Current Price -->
									<td class="border-r border-gray-600 px-2 py-2 text-right sm:px-4 sm:py-3">
										{#if asset.type === 'cash'}
											-
										{:else}
											{formatValuation(valuation?.currentPrice)}
										{/if}
									</td>

									<!-- 7. Value -->
									<td class="border-r border-gray-600 px-2 py-2 text-right sm:px-4 sm:py-3">
										{formatValuation(valuation?.value)}
									</td>

									<!-- 8. Yield -->
									<td class="border-r border-gray-600 px-2 py-2 text-right sm:px-4 sm:py-3">
										{#if asset.type === 'cash'}
											-
										{:else}
											<span
												class={valuation?.yield == null
													? 'text-text-light'
													: valuation.yield >= 0
														? 'text-profit'
														: 'text-loss'}
											>
												{formatValuation(valuation?.yield)}
											</span>
										{/if}
									</td>

									<!-- 9. Performance -->
									<td class="border-r border-gray-600 px-2 py-2 text-right sm:px-4 sm:py-3">
										{#if asset.type === 'cash'}
											-
										{:else}
											<span
												class={valuation?.performance == null
													? 'text-text-light'
													: valuation.performance >= 0
														? 'text-profit'
														: 'text-loss'}
											>
												{formatValuation(valuation?.performance, true)}
											</span>
										{/if}
									</td>

									<!-- 10. Status -->
									<td class="px-2 py-2 text-center sm:px-4 sm:py-3">
										{#if cacheStatusMap.has(asset.id)}
											{@const cacheStatus = cacheStatusMap.get(asset.id)}
											{#if cacheStatus}
												<CacheStatusIndicator
													cachedAt={cacheStatus.cached_at}
													cacheTtlMinutes={cacheStatus.cache_ttl_minutes}
													assetType={asset.type}
													assetId={asset.id}
													showExpirationTime={true}
													showLabel={false}
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
							<tr class="bg-background border-gold border-t-2 font-bold">
								<!-- 1-2. Location/Broker + Type (colspan=2) -->
								<td class="border-r border-gray-600 px-4 py-3" colspan="2">
									<span class="text-gold">TOTAL ({sortedAssets.length} assets)</span>
								</td>
								<!-- 3. Asset -->
								<td class="border-r border-gray-600 px-4 py-3 text-center">-</td>
								<!-- 4. Quantity -->
								<td class="border-r border-gray-600 px-4 py-3 text-center">-</td>
								<!-- 5. Purchase Price -->
								<td class="border-r border-gray-600 px-4 py-3 text-center">-</td>
								<!-- 6. Current Price -->
								<td class="border-r border-gray-600 px-4 py-3 text-center">-</td>
								<!-- 7. Value -->
								<td
									class="text-gold border-r border-gray-600 px-4 py-3 text-right text-lg font-bold"
								>
									{#if totalValue === null}
										<span
											class="text-text-light"
											title="A quote or currency conversion is unavailable."
											>{isCalculatingTotals ? '...' : 'Unavailable'}</span
										>
									{:else}
										{formatCurrency(totalValue, totalCurrency)}
									{/if}
								</td>
								<!-- 8. Yield -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if totalYield === null}
										<span title="Quote, purchase cost, or currency conversion unavailable."
											>{isCalculatingTotals ? '...' : 'Unavailable'}</span
										>
									{:else}
										<span class={totalYield >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}
											>{formatCurrency(totalYield, totalCurrency)}</span
										>
									{/if}
								</td>
								<!-- 9. Performance -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if totalPerformance === null}
										<span title="Return requires complete values and a nonzero cost basis."
											>{isCalculatingTotals ? '...' : 'Unavailable'}</span
										>
									{:else}
										<span
											class={totalPerformance >= 0
												? 'text-profit font-bold'
												: 'text-loss font-bold'}>{formatPercentage(totalPerformance)}</span
										>
									{/if}
								</td>
								<!-- 10. Status -->
								<td class="px-4 py-3 text-center"
									><span role="status"
										>{isCalculatingTotals
											? 'Calculating...'
											: totalValue === null || totalYield === null || totalPerformance === null
												? 'Incomplete'
												: '-'}</span
									></td
								>
							</tr>
						</tfoot>
					</table>
				</div>
			{:else}
				<p class="py-4 text-center">No matching assets found.</p>
			{/if}
		</main>
	{:else if activeTab === 'distribution'}
		<!-- Distribution Tab Content -->
		<main class="bg-surface rounded-lg p-4 shadow-lg sm:p-6">
			<div class="mb-4">
				<h2 class="font-headline text-xl sm:text-2xl">Asset Distribution</h2>
			</div>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<!-- Asset Type Distribution Chart -->
				<div class="bg-background rounded-lg p-6">
					<h3 class="font-headline text-gold mb-4 text-lg">By Asset Type</h3>
					<AssetTypePieChart assets={sortedAssets} {totalCurrency} {assetPrices} {refreshTrigger} />
				</div>

				<div class="bg-background rounded-lg p-6">
					<h3 class="font-headline text-gold mb-4 text-lg">By Broker</h3>
					<BrokerPieChart assets={sortedAssets} {totalCurrency} {assetPrices} {refreshTrigger} />
				</div>

				<div class="bg-background rounded-lg p-6">
					<h3 class="font-headline text-gold mb-4 text-lg">Asset Performance</h3>
					<AssetPerformanceChart
						assets={sortedAssets}
						{totalCurrency}
						{assetPrices}
						{refreshTrigger}
					/>
				</div>

				<div class="bg-background rounded-lg p-6">
					<h3 class="font-headline text-gold mb-4 text-lg">Top Holdings</h3>
					<TopHoldings
						assets={sortedAssets}
						{totalCurrency}
						{assetPrices}
						{refreshTrigger}
						maxHoldings={10}
					/>
				</div>
			</div>
		</main>
	{:else if activeTab === 'analytics'}
		<!-- Analytics Tab Content -->
		<main class="bg-surface rounded-lg p-4 shadow-lg sm:p-6">
			<div class="mb-4">
				<h2 class="font-headline text-xl sm:text-2xl">Portfolio Analytics</h2>
			</div>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<!-- Portfolio Efficiency -->
				<div class="bg-background rounded-lg p-6">
					<PortfolioEfficiency assets={sortedAssets} {assetPrices} {refreshTrigger} />
				</div>

				<!-- Portfolio Risk Score -->
				<div class="bg-background rounded-lg p-6">
					<PortfolioRiskScore assets={sortedAssets} {assetPrices} {refreshTrigger} />
				</div>
			</div>
		</main>
	{/if}
</div>
