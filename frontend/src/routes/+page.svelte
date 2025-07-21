<script lang="ts">
	import ValueCell from '$lib/components/ValueCell.svelte';
	import CacheStatusIndicator from '$lib/components/CacheStatusIndicator.svelte';
	import ProfitLossCell from '$lib/components/ProfitLossCell.svelte';
	import CacheStatusBanner from '$lib/components/CacheStatusBanner.svelte';
	import CurrencyRateDisplay from '$lib/components/CurrencyRateDisplay.svelte';
	import { refreshAllPrices } from '$lib/services/api';
	import * as enhancedApi from '$lib/services/enhancedApi';
	import type { Asset } from '$lib/types';
	import type { RefreshAllResponse, AssetCacheStatus } from '$lib/types';
	import { refreshAssetCacheStatus } from '$lib/stores/assetStatusStore';
	import { getContext } from 'svelte';
	import AddAssetForm from '$lib/components/AddAssetForm.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { PriceManagementService } from '$lib/services/priceManagement';
	import { PortfolioCalculationService } from '$lib/services/portfolioCalculations';
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
				const priceValue = 'price' in value ? (value.price as number) : 0;
				const currencyValue = 'currency' in value ? (value.currency as string) : 'USD';

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
			console.log(
				`Using ${assetPrices.size} prices from initial page load (${cacheInfo?.cacheHits || 0} from cache, ${cacheInfo?.apiCalls || 0} from API, ${cacheInfo?.cacheEfficiency?.toFixed(1) || 0}% cache efficiency)`
			);
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
	let filterType: 'all' | 'cash' | 'stock' | 'crypto' = 'all';

	// Sorting state
	type SortField =
		| 'location'
		| 'asset'
		| 'type'
		| 'currentPrice'
		| 'value'
		| 'quantity'
		| 'purchasePrice'
		| 'performance'
		| 'yield';
	let sortField: SortField | null = null;
	let sortDirection: 'asc' | 'desc' = 'asc';

	// Initialize services
	const priceManagementService = new PriceManagementService();
	let portfolioCalculationService: PortfolioCalculationService;

	// Initialize the price management service with loaded prices
	$: if (assetPrices.size > 0 && !priceManagementService.isPricesLoaded()) {
		// Set the prices in the service
		priceManagementService.setPrices(assetPrices);
		console.log(`Initialized PriceManagementService with ${assetPrices.size} prices`);
	}

	// Helper function to get current price for an asset
	function getCurrentPrice(asset: Asset): number {
		if (asset.type === 'cash') {
			return 1; // Cash has no price, value is just quantity
		}

		// Get price from the price management service
		const price = priceManagementService.getCurrentPrice(asset);

		// Debug log for price retrieval
		console.debug(`Price for asset ${asset.id} (${asset.symbol}): ${price}`);

		return price;
	}

	// Helper function to calculate current value (for sorting) - mirrors ValueCell logic
	async function calculateCurrentValue(asset: Asset): Promise<number> {
		if (asset.type === 'cash') {
			return asset.quantity;
		}

		try {
			const symbol = asset.symbol || '';
			const currency = asset.buy_currency || asset.currency || 'USD';

			if (!symbol) return 0;

			// Use enhanced API with cache-first approach
			const priceData = await enhancedApi.getPrice(symbol, asset.type, { forceRefresh: false });

			if (!priceData || !priceData.price) return 0;

			let price = priceData.price;
			let priceCurrency = priceData.currency || 'USD';

			// Convert to total currency if needed using cache-first approach
			if (currency && currency !== priceCurrency) {
				const conversionData = await enhancedApi.convertCurrency(priceCurrency, currency, price, {
					forceRefresh: false
				});
				price = conversionData.converted;
			}

			return price * asset.quantity;
		} catch (error) {
			console.error(`Error calculating current value for ${asset.symbol}:`, error);
			return 0;
		}
	}

	// Helper function to calculate profit/loss (for sorting) - mirrors ProfitLossCell logic
	async function calculateProfitLoss(asset: Asset): Promise<number> {
		if (asset.type === 'cash' || !asset.purchase_price) {
			return 0;
		}

		try {
			const symbol = asset.symbol || '';
			const currency = asset.buy_currency || asset.currency || 'USD';

			if (!symbol) return 0;

			// Use enhanced API with cache-first approach
			const priceData = await enhancedApi.getPrice(symbol, asset.type, { forceRefresh: false });

			if (!priceData || !priceData.price) return 0;

			let currentPrice = priceData.price;
			let priceCurrency = priceData.currency || 'USD';

			// Convert to asset currency if needed using cache-first approach
			if (currency && currency !== priceCurrency) {
				const conversionData = await enhancedApi.convertCurrency(
					priceCurrency,
					currency,
					currentPrice,
					{ forceRefresh: false }
				);
				currentPrice = conversionData.converted;
			}

			const totalCurrentValue = currentPrice * asset.quantity;
			const totalPurchaseValue = asset.purchase_price * asset.quantity;

			return totalCurrentValue - totalPurchaseValue;
		} catch (error) {
			console.error(`Error calculating profit/loss for ${asset.symbol}:`, error);
			return 0;
		}
	}

	// Helper function to calculate performance percentage (for sorting) - mirrors ProfitLossCell logic
	async function calculatePerformancePercentage(asset: Asset): Promise<number> {
		if (asset.type === 'cash' || !asset.purchase_price) {
			return 0;
		}

		try {
			const symbol = asset.symbol || '';
			const currency = asset.buy_currency || asset.currency || 'USD';

			if (!symbol) return 0;

			// Use enhanced API with cache-first approach
			const priceData = await enhancedApi.getPrice(symbol, asset.type, { forceRefresh: false });

			if (!priceData || !priceData.price) return 0;

			let currentPrice = priceData.price;
			let priceCurrency = priceData.currency || 'USD';

			// Convert to asset currency if needed using cache-first approach
			if (currency && currency !== priceCurrency) {
				const conversionData = await enhancedApi.convertCurrency(
					priceCurrency,
					currency,
					currentPrice,
					{ forceRefresh: false }
				);
				currentPrice = conversionData.converted;
			}

			return ((currentPrice - asset.purchase_price) / asset.purchase_price) * 100;
		} catch (error) {
			console.error(`Error calculating performance for ${asset.symbol}:`, error);
			return 0;
		}
	}

	// Cache for calculated values to avoid repeated API calls during sorting
	let calculatedValues: Map<number, { value: number; profitLoss: number; performance: number }> =
		new Map();

	// Function to calculate all values for sorting
	async function calculateAllValuesForSorting(assets: Asset[]): Promise<void> {
		console.log('Calculating all values for sorting...');

		const calculations = assets.map(async (asset) => {
			if (asset.type === 'cash') {
				calculatedValues.set(asset.id, {
					value: asset.quantity,
					profitLoss: 0,
					performance: 0
				});
				return;
			}

			try {
				const [value, profitLoss, performance] = await Promise.all([
					calculateCurrentValue(asset),
					calculateProfitLoss(asset),
					calculatePerformancePercentage(asset)
				]);

				calculatedValues.set(asset.id, {
					value,
					profitLoss,
					performance
				});
			} catch (error) {
				console.error(`Error calculating values for ${asset.symbol}:`, error);
				calculatedValues.set(asset.id, {
					value: 0,
					profitLoss: 0,
					performance: 0
				});
			}
		});

		await Promise.all(calculations);
		console.log('All values calculated for sorting');
	}

	// Sort function
	async function sortAssets(
		assets: Asset[],
		field: SortField | null,
		direction: 'asc' | 'desc'
	): Promise<Asset[]> {
		if (!field) return assets;

		// Calculate all values for sorting
		await calculateAllValuesForSorting(assets);

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
					aVal = calculatedValues.get(a.id)?.value || 0;
					bVal = calculatedValues.get(b.id)?.value || 0;
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
					aVal = calculatedValues.get(a.id)?.performance || 0;
					bVal = calculatedValues.get(b.id)?.performance || 0;
					// Handle cases where one or both assets have no performance data
					if (isNaN(aVal)) aVal = 0;
					if (isNaN(bVal)) bVal = 0;
					break;
				case 'yield':
					aVal = calculatedValues.get(a.id)?.profitLoss || 0;
					bVal = calculatedValues.get(b.id)?.profitLoss || 0;
					break;
				default:
					return 0;
			}

			// Handle string comparison
			if (typeof aVal === 'string' && typeof bVal === 'string') {
				return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
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
	async function fetchAllCurrentPrices(forceRefresh = false) {
		console.log(`=== fetchAllCurrentPrices START (forceRefresh: ${forceRefresh}) ===`);

		try {
			// If we already have prices loaded from the page data and we're not forcing refresh,
			// we can skip the API calls and use what we have
			if (pricesLoaded && !forceRefresh && assetPrices.size > 0) {
				console.log('Using prices already loaded from page data (skipping API calls)');
				return;
			}

			// Use the price management service to fetch all prices
			// Pass the forceRefresh parameter to respect cache when appropriate
			const pricesMap = await priceManagementService.fetchAllCurrentPrices(allAssets, forceRefresh);

			// Update the local variables
			assetPrices = pricesMap;
			pricesLoaded = true;

			// Initialize the portfolio calculation service with the updated prices
			portfolioCalculationService = new PortfolioCalculationService(assetPrices);

			console.log('Updated assetPrices Map:', Array.from(assetPrices.entries()));
			console.log('=== fetchAllCurrentPrices END ===');
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

				// Initialize portfolio calculation service with existing prices
				if (!portfolioCalculationService) {
					portfolioCalculationService = new PortfolioCalculationService(assetPrices);
				}
			} else {
				// No prices available, show a warning
				console.warn(`No prices available due to ${errorSource}: ${errorMessage}`);
			}
		}
	}

	$: filteredAssets = allAssets.filter((asset) => {
		const locationMatch =
			!filterLocation || asset.name.toLowerCase().includes(filterLocation.toLowerCase());
		const symbolMatch =
			!filterSymbol ||
			(asset.symbol && asset.symbol.toLowerCase().includes(filterSymbol.toLowerCase()));
		const typeMatch = filterType === 'all' || asset.type === filterType;
		return locationMatch && symbolMatch && typeMatch;
	});

	let sortedAssets: Asset[] = [];

	// Function to update sorted assets
	async function updateSortedAssets() {
		sortedAssets = await sortAssets(filteredAssets, sortField, sortDirection);
	}

	// React to changes in filtered assets or sort parameters
	$: if (filteredAssets && sortField && sortDirection) {
		updateSortedAssets();
	}

	// Also update when data changes
	$: if (filteredAssets) {
		updateSortedAssets();
	}

	// Reactive totals that update when pricesLoaded or totalCurrency changes
	let totalValue = 0;
	let totalYield = 0;
	let totalPerformance = 0;

	// Function to update all totals
	async function updateTotals() {
		console.log('Calculating totals directly from visible assets');

		try {
			// Calculate totals directly from the visible assets
			let sumValue = 0;
			let sumInvestment = 0;
			let sumYield = 0;

			console.log(`Processing ${sortedAssets.length} assets for totals`);

			// Process each asset and convert to total currency
			for (const asset of sortedAssets) {
				// Handle cash assets
				if (asset.type === 'cash') {
					let cashValue = asset.quantity || 0;
					const assetCurrency = asset.currency || 'USD';

					// Convert cash to total currency if needed
					if (assetCurrency !== totalCurrency) {
						try {
							const conversionData = await enhancedApi.convertCurrency(
								assetCurrency,
								totalCurrency,
								cashValue,
								{ forceRefresh: false }
							);
							cashValue = conversionData.converted;
						} catch (error) {
							console.error(`Failed to convert ${assetCurrency} to ${totalCurrency}:`, error);
							// Use original value if conversion fails
						}
					}

					console.log(
						`Cash asset ${asset.name}: ${cashValue} ${totalCurrency} (from ${asset.quantity} ${assetCurrency})`
					);
					sumValue += cashValue;
					continue;
				}

				// Handle stock and crypto assets
				if (asset.type === 'stock' || asset.type === 'crypto') {
					// Get the current price from the price management service
					const currentPrice = getCurrentPrice(asset);
					const quantity = asset.quantity || 0;
					let currentValue = currentPrice * quantity;

					// The price should already be in the correct currency from the price service
					// But let's ensure it's converted to total currency if needed
					const assetCurrency = asset.buy_currency || asset.currency || 'USD';
					if (assetCurrency !== totalCurrency) {
						try {
							const conversionData = await enhancedApi.convertCurrency(
								assetCurrency,
								totalCurrency,
								currentValue,
								{ forceRefresh: false }
							);
							currentValue = conversionData.converted;
						} catch (error) {
							console.error(`Failed to convert ${assetCurrency} to ${totalCurrency}:`, error);
							// Use original value if conversion fails
						}
					}

					console.log(
						`${asset.type} asset ${asset.symbol}: Price=${currentPrice}, Quantity=${quantity}, Value=${currentValue} ${totalCurrency}`
					);

					// Add to total value
					sumValue += currentValue;

					// Calculate yield if purchase price is available
					if (asset.purchase_price && asset.purchase_price > 0) {
						let purchaseValue = asset.purchase_price * quantity;

						// Convert purchase value to total currency if needed
						const purchaseCurrency = asset.buy_currency || asset.currency || 'USD';
						if (purchaseCurrency !== totalCurrency) {
							try {
								const conversionData = await enhancedApi.convertCurrency(
									purchaseCurrency,
									totalCurrency,
									purchaseValue,
									{ forceRefresh: false }
								);
								purchaseValue = conversionData.converted;
							} catch (error) {
								console.error(
									`Failed to convert purchase value from ${purchaseCurrency} to ${totalCurrency}:`,
									error
								);
								// Use original value if conversion fails
							}
						}

						const assetYield = currentValue - purchaseValue;

						console.log(
							`  Purchase: ${asset.purchase_price} ${purchaseCurrency}, PurchaseValue: ${purchaseValue} ${totalCurrency}, Yield: ${assetYield} ${totalCurrency}`
						);

						sumYield += assetYield;
						sumInvestment += purchaseValue;
					}
				}
			}

			// Set the calculated totals
			totalValue = sumValue;
			totalYield = sumYield;

			// Calculate performance percentage
			totalPerformance = sumInvestment > 0 ? (sumYield / sumInvestment) * 100 : 0;

			console.log('Calculated totals:', {
				totalValue,
				totalYield,
				totalPerformance,
				sumInvestment,
				currency: totalCurrency
			});
		} catch (error) {
			console.error('Error calculating totals:', error);
			totalValue = 0;
			totalYield = 0;
			totalPerformance = 0;
		}
	}

	// Update totals when prices are loaded or currency changes
	$: if (pricesLoaded || totalCurrency) {
		console.log('Trigger totals update:', { pricesLoaded, totalCurrency });
		updateTotals();
	}

	// Also update totals when sorted assets change
	$: if (sortedAssets && sortedAssets.length > 0) {
		console.log('Assets changed, updating totals');
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
			// Use the centralized cache store refresh function
			await refreshAssetCacheStatus();
		} catch (error) {
			console.error('Failed to reload cache status:', error);
		}
	}

	// Periodically reload cache status to keep it current
	let cacheStatusInterval: number;
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
			console.log('Fetching all prices on page load with cache-first approach');
			// Don't force refresh, use cache-first approach
			await fetchAllCurrentPrices(false);

			// Update totals after prices are loaded
			await updateTotals();
		}

		// Set up the adaptive cache polling
		setupAdaptiveCachePolling();

		// Initialize the cache status
		await enhancedApi.getFrontendCacheStats();
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
			console.log('Manually refreshing all asset prices (bypassing cache)...');

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
			}, 1500);

			console.log('Manual price refresh completed successfully:', refreshResult);

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

<div class="bg-background text-text-light min-h-screen p-8">
	<header class="mb-8">
		<h1 class="font-headline text-gold text-4xl">Cointainr</h1>
	</header>

	<CacheStatusBanner {lastRefreshTime} />

	<section class="bg-surface mb-8 flex items-center justify-between rounded-lg p-4">
		<div class="flex items-center gap-4">
			<input
				type="text"
				bind:value={filterLocation}
				placeholder="Location/Broker..."
				class="bg-background text-text-light rounded p-2"
			/>
			<input
				type="text"
				bind:value={filterSymbol}
				placeholder="Symbol/ISIN..."
				class="bg-background text-text-light rounded p-2"
			/>
			<select bind:value={filterType} class="bg-background text-text-light rounded p-2">
				<option value="all">All Types</option>
				<option value="cash">Cash</option>
				<option value="stock">Stock</option>
				<option value="crypto">Crypto</option>
			</select>
			<div class="ml-4 flex items-center gap-2 border-l border-gray-600 pl-4">
				<label for="totalCurrency" class="text-text-light text-sm">Totals in:</label>
				<select
					id="totalCurrency"
					bind:value={totalCurrency}
					class="bg-background text-text-light rounded border border-gray-600 px-3 py-1"
				>
					<option value="EUR">EUR</option>
					<option value="USD">USD</option>
					<option value="GBP">GBP</option>
					<option value="CHF">CHF</option>
				</select>

				<!-- Compact Currency Rate Display -->
				<CurrencyRateDisplay baseCurrency={totalCurrency} assets={allAssets} />
			</div>
		</div>
		<div class="flex items-center gap-4">
			<!-- Cache status is now handled by CacheStatusBanner component -->
			<button
				on:click={handleRefreshAllPrices}
				disabled={isRefreshing}
				class="bg-primary border-primary flex items-center justify-center gap-2 rounded border p-2 font-bold text-white hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-50"
				title="Force refresh all prices (bypass cache)"
				aria-label="Force refresh all prices"
			>
				<svg
					class="h-5 w-5"
					class:animate-spin={isRefreshing}
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					xmlns="http://www.w3.org/2000/svg"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
					></path>
				</svg>
				<span class="hidden text-sm sm:inline">Force Refresh</span>
			</button>
			<button
				on:click={openAddModal}
				class="bg-gold rounded px-4 py-2 font-bold text-white hover:opacity-80"
			>
				Add Asset
			</button>
		</div>
	</section>

	<main class="bg-surface rounded-lg p-6 shadow-lg">
		<div class="mb-4 flex items-center justify-between">
			<h2 class="font-headline text-2xl">Assets</h2>
			<div class="text-sm text-gray-400">
				Last refresh: {formatLastRefresh(lastRefreshTime)}
			</div>
		</div>

		<!-- No need for additional refresh button as we have Force Refresh in the nav bar -->
		{#if sortedAssets.length > 0}
			<div class="overflow-hidden rounded-lg">
				<table class="rounded-table w-full border-collapse border border-gray-600 font-mono">
					<thead>
						<tr class="bg-background border-b-2 border-gray-600">
							<th
								class="hover:bg-surface col-span-2 cursor-pointer border-r border-gray-600 px-4 py-3 text-left font-bold transition-colors"
								on:click={() => handleSort('location')}
							>
								<div class="flex items-center justify-between">
									Location/Broker
									{#if sortField === 'location'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-left font-bold transition-colors"
								on:click={() => handleSort('type')}
							>
								<div class="flex items-center justify-between">
									Type
									{#if sortField === 'type'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-left font-bold transition-colors"
								on:click={() => handleSort('asset')}
							>
								<div class="flex items-center justify-between">
									Asset
									{#if sortField === 'asset'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-right font-bold transition-colors"
								on:click={() => handleSort('quantity')}
							>
								<div class="flex items-center justify-end">
									Quantity
									{#if sortField === 'quantity'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-right font-bold transition-colors"
								on:click={() => handleSort('purchasePrice')}
							>
								<div class="flex items-center justify-end">
									Purchase Price
									{#if sortField === 'purchasePrice'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-right font-bold transition-colors"
								on:click={() => handleSort('currentPrice')}
							>
								<div class="flex items-center justify-end">
									Current Price
									{#if sortField === 'currentPrice'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-right font-bold transition-colors"
								on:click={() => handleSort('value')}
							>
								<div class="flex items-center justify-end">
									Value
									{#if sortField === 'value'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-right font-bold transition-colors"
								on:click={() => handleSort('yield')}
							>
								<div class="flex items-center justify-end">
									Yield
									{#if sortField === 'yield'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th
								class="hover:bg-surface cursor-pointer border-r border-gray-600 px-4 py-3 text-right font-bold transition-colors"
								on:click={() => handleSort('performance')}
							>
								<div class="flex items-center justify-end">
									Performance
									{#if sortField === 'performance'}
										<span class="text-primary ml-2">
											{sortDirection === 'asc' ? '↑' : '↓'}
										</span>
									{:else}
										<span class="ml-2 text-gray-500">↕</span>
									{/if}
								</div>
							</th>
							<th class="px-4 py-3 text-center font-bold">Status</th>
						</tr>
					</thead>
					<tbody>
						{#each sortedAssets as asset (asset.id)}
							<tr
								tabindex="0"
								on:click={() => openEditModal(asset)}
								on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && openEditModal(asset)}
								class="hover:bg-surface focus:ring-primary cursor-pointer border-b border-gray-600 transition-colors focus:outline-none focus:ring-2"
								aria-label={`Edit asset ${asset.name}`}
							>
								<!-- 1. Location/Broker -->
								<td class="col-span-2 border-r border-gray-600 px-4 py-3">{asset.name}</td>

								<!-- 2. Type -->
								<td class="border-r border-gray-600 px-4 py-3 capitalize">{asset.type}</td>

								<!-- 3. Asset -->
								<td class="border-r border-gray-600 px-4 py-3"
									>{asset.assetname ?? asset.symbol ?? '-'}</td
								>

								<!-- 4. Quantity -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if asset.type === 'cash'}
										-
									{:else}
										{formatNumber(asset.quantity)}
									{/if}
								</td>

								<!-- 5. Purchase Price -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if asset.purchase_price}
										{formatCurrency(
											asset.purchase_price,
											asset.buy_currency ?? asset.currency ?? ''
										)}
									{:else}
										-
									{/if}
								</td>

								<!-- 6. Current Price -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if asset.type === 'cash'}
										-
									{:else if asset.type === 'stock' || asset.type === 'crypto'}
										<ValueCell
											symbol={asset.symbol ?? ''}
											quantity={1}
											currency={asset.buy_currency ?? asset.currency ?? 'USD'}
											assetType={asset.type}
											{refreshTrigger}
											showCacheStatus={false}
										/>
									{:else}
										-
									{/if}
								</td>

								<!-- 7. Value -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if asset.type === 'cash'}
										{formatCurrency(asset.quantity, asset.currency ?? 'EUR')}
									{:else if asset.type === 'stock' || asset.type === 'crypto'}
										<ValueCell
											symbol={asset.symbol ?? ''}
											quantity={asset.quantity}
											currency={asset.buy_currency ?? asset.currency ?? 'USD'}
											assetType={asset.type}
											{refreshTrigger}
											showCacheStatus={false}
										/>
									{:else}
										-
									{/if}
								</td>

								<!-- 8. Yield -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if asset.type === 'cash'}
										-
									{:else if asset.type === 'stock' || asset.type === 'crypto'}
										<ProfitLossCell
											symbol={asset.symbol ?? ''}
											quantity={asset.quantity}
											purchasePrice={asset.purchase_price}
											currency={asset.buy_currency ?? asset.currency ?? 'USD'}
											assetType={asset.type}
											{refreshTrigger}
											displayType="absolute"
											showCacheStatus={false}
										/>
									{:else}
										-
									{/if}
								</td>

								<!-- 9. Performance -->
								<td class="border-r border-gray-600 px-4 py-3 text-right">
									{#if asset.type === 'cash'}
										-
									{:else if asset.type === 'stock' || asset.type === 'crypto'}
										<ProfitLossCell
											symbol={asset.symbol ?? ''}
											quantity={asset.quantity}
											purchasePrice={asset.purchase_price}
											currency={asset.buy_currency ?? asset.currency ?? 'USD'}
											assetType={asset.type}
											{refreshTrigger}
											displayType="percentage"
											showCacheStatus={false}
										/>
									{:else}
										-
									{/if}
								</td>

								<!-- 10. Status -->
								<td class="px-4 py-3 text-center">
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
							<td class="text-gold border-r border-gray-600 px-4 py-3 text-right text-lg font-bold">
								{formatCurrency(totalValue, totalCurrency)}
							</td>
							<!-- 8. Yield -->
							<td class="border-r border-gray-600 px-4 py-3 text-right">
								<span class={totalYield >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}>
									{formatCurrency(totalYield, totalCurrency)}
								</span>
							</td>
							<!-- 9. Performance -->
							<td class="border-r border-gray-600 px-4 py-3 text-right">
								<span
									class={totalPerformance >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}
								>
									{formatPercentage(totalPerformance)}
								</span>
							</td>
							<!-- 10. Status -->
							<td class="px-4 py-3 text-center">-</td>
						</tr>
					</tfoot>
				</table>
			</div>
		{:else}
			<p class="py-4 text-center">No matching assets found.</p>
		{/if}
	</main>
</div>
