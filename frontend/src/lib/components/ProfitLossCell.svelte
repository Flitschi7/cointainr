<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import type { PriceResponse } from '$lib/types';
	import { formatPercentage, formatCurrency } from '$lib/utils/numberFormat';
	import CacheIndicator from './CacheIndicator.svelte';
	import ErrorState from './ErrorState.svelte';
	import TransitionWrapper from './TransitionWrapper.svelte';
	import TableCellSkeleton from './TableCellSkeleton.svelte';
	import * as enhancedApi from '$lib/services/enhancedApi';
	import * as apiWithRetry from '$lib/services/apiWithRetry';

	export let symbol: string;
	export let quantity: number;
	export let purchasePrice: number | null;
	export let currency: string;
	export let assetType: 'stock' | 'crypto';
	export let refreshTrigger: number = 0;
	export let displayType: 'percentage' | 'absolute' = 'percentage';
	export let showCacheStatus: boolean = false; // Whether to show cache status indicator

	let currentPrice: number | null = null;
	let profitLoss: number | null = null;
	let profitLossPercentage: number | null = null;
	let isLoading = true;
	let error: string | null = null;
	let errorDetails: string | null = null;
	let isCached: boolean = false; // Track if the current data is from cache
	let lastUpdated: string | null = null; // Track when the data was last updated
	let isStale: boolean = false; // Track if the cached data is stale
	let retryCount = 0;
	let maxRetries = 3;

	// Memoized values to prevent unnecessary calculations
	let formattedDisplayValue: string = '-';
	let displayColorClass: string = '';
	let cacheStatusProps: { isCached: boolean; lastUpdated: string | null; isStale: boolean } = {
		isCached: false,
		lastUpdated: null,
		isStale: false
	};
	let displayValue: number | null = null;

	// Memoize the display value calculation
	$: displayValue = displayType === 'percentage' ? profitLossPercentage : profitLoss;

	// Memoize the formatted value calculation
	$: if (displayValue !== null) {
		formattedDisplayValue = formatValue(displayValue);
		displayColorClass = getColorClass(displayValue);
	} else {
		formattedDisplayValue = '-';
		displayColorClass = '';
	}

	// Memoize cache status props to prevent unnecessary object creation
	$: cacheStatusProps = {
		isCached,
		lastUpdated,
		isStale
	};

	onMount(async () => {
		if (browser && purchasePrice) {
			// Use cache-first approach when component mounts
			await fetchPriceAndCalculate(false);
		}
	});

	// Track the last refresh trigger to avoid duplicate fetches
	let lastRefreshTrigger = 0;
	$: if (browser && refreshTrigger > 0 && refreshTrigger !== lastRefreshTrigger && purchasePrice) {
		fetchPriceAndCalculate(true); // Force refresh when triggered manually
	}

	// Update the last refresh trigger when it changes
	$: if (refreshTrigger > lastRefreshTrigger) {
		lastRefreshTrigger = refreshTrigger;
	}

	async function fetchPriceAndCalculate(shouldForceRefresh: boolean = false) {
		// Skip calculation if purchase price is not available
		if (!purchasePrice) {
			isLoading = false;
			return;
		}

		// Store previous values for fallback in case of errors
		const previousProfitLoss = profitLoss;
		const previousProfitLossPercentage = profitLossPercentage;

		try {
			isLoading = true;
			error = null;
			errorDetails = null;

			// Use the API with retry logic
			const priceData = await apiWithRetry.getPrice(symbol, assetType, {
				forceRefresh: shouldForceRefresh
			});

			// Check if we got valid price data
			if (priceData && priceData.price !== undefined) {
				currentPrice = priceData.price;

				// Get cache status information - only when needed
				const cacheInfo = enhancedApi.getAssetCacheInfo(symbol, assetType);
				isCached = cacheInfo.isCached;
				isStale = !cacheInfo.isValid && cacheInfo.isCached;
				lastUpdated = priceData.fetched_at || null;

				// Convert current price to purchase currency if needed
				let convertedCurrentPrice = currentPrice;
				if (priceData.currency && priceData.currency !== currency) {
					try {
						// Use cache-first approach for currency conversion with retry
						const conversionData = await apiWithRetry.convertCurrency(
							priceData.currency,
							currency,
							currentPrice,
							{ forceRefresh: shouldForceRefresh }
						);

						if (conversionData.converted !== undefined) {
							convertedCurrentPrice = conversionData.converted;
						}
					} catch (convError) {
						console.warn('Currency conversion failed, using original price:', convError);
						// Still continue with the original price
					}
				}

				// Calculate profit/loss - only once with all data available
				const totalCurrentValue = convertedCurrentPrice * quantity;
				const totalPurchaseValue = purchasePrice * quantity;

				profitLoss = totalCurrentValue - totalPurchaseValue;
				profitLossPercentage = ((convertedCurrentPrice - purchasePrice) / purchasePrice) * 100;

				// Only log in debug mode to reduce console noise
				if (process.env.NODE_ENV !== 'production') {
					console.debug(
						`${symbol} profit/loss calculation: ${isCached ? 'Using cached data' : 'Using fresh data'}`
					);
				}

				retryCount = 0; // Reset retry count on success
			} else {
				error = 'Failed to get price';
			}
		} catch (e: any) {
			handleError(e, previousProfitLoss, previousProfitLossPercentage);
		} finally {
			isLoading = false;
		}
	}

	function handleError(
		e: any,
		previousProfitLoss: number | null,
		previousProfitLossPercentage: number | null
	): void {
		// If we have previous values, keep them and just show a warning
		if (previousProfitLoss !== null && previousProfitLossPercentage !== null) {
			profitLoss = previousProfitLoss;
			profitLossPercentage = previousProfitLossPercentage;
			isCached = true; // Mark as cached since we're using previous value
			isStale = true; // Mark as stale since we couldn't refresh

			// Provide more detailed error information
			const errorMessage = e.message || 'Unknown error';
			const originalMessage = e.originalMessage || errorMessage;

			// Determine error type for better user feedback
			let errorSource = 'API error';

			if (e.isNetworkError || (originalMessage && originalMessage.includes('network'))) {
				errorSource = 'Network error';
			} else if (originalMessage && originalMessage.includes('timeout')) {
				errorSource = 'API timeout';
			} else if (e.category === 'rate-limit') {
				errorSource = 'Rate limit exceeded';
			} else if (e.status === 404) {
				errorSource = 'Resource not found';
			}

			console.warn(`Using cached profit/loss values for ${symbol} due to ${errorSource}:`, e);

			// Set a non-blocking error that won't prevent display but will show in tooltip
			error = `Using cached data. ${errorSource}`;
			errorDetails = originalMessage;
		} else {
			// No previous value to fall back to
			error = 'Error calculating profit/loss';
			errorDetails = e.originalMessage || e.message || 'Unable to calculate profit/loss';
			console.error('Error calculating profit/loss:', e);
		}
	}

	// Function to retry fetching with exponential backoff
	async function retryFetch() {
		if (retryCount >= maxRetries) {
			error = `Failed after ${maxRetries} retry attempts`;
			return;
		}

		retryCount++;
		await fetchPriceAndCalculate(true);
	}

	// Memoized formatting function to prevent recalculation
	function formatValue(value: number | null): string {
		if (value === null) return '-';

		if (displayType === 'percentage') {
			return formatPercentage(value);
		} else {
			return formatCurrency(value, currency);
		}
	}

	// Memoized color class function to prevent recalculation
	function getColorClass(value: number | null): string {
		if (value === null) return '';
		if (value > 0) return 'text-profit';
		if (value < 0) return 'text-loss';
		return '';
	}
</script>

{#if !purchasePrice}
	<span class="text-gray-400">-</span>
{:else}
	<TransitionWrapper {isLoading} transitionType="fade" transitionDuration={150}>
		<svelte:fragment slot="loading">
			<TableCellSkeleton width="4rem" />
		</svelte:fragment>

		{#if error && displayValue === null}
			<ErrorState
				message="Error"
				details={errorDetails || error}
				severity="error"
				inline={true}
				onRetry={retryFetch}
			/>
		{:else if error && displayValue !== null}
			<span class="profit-loss-cell">
				<span class={getColorClass(displayValue)}>
					{formatValue(displayValue)}
				</span>
				<ErrorState
					message="!"
					details={error}
					severity="warning"
					inline={true}
					showIcon={false}
					onRetry={retryFetch}
				/>
				{#if showCacheStatus}
					<span class="ml-1">
						<CacheIndicator {isCached} {lastUpdated} {isStale} />
					</span>
				{/if}
			</span>
		{:else}
			<span class="profit-loss-cell">
				<span class={getColorClass(displayValue)}>
					{formatValue(displayValue)}
				</span>
				{#if showCacheStatus}
					<span class="ml-1">
						<CacheIndicator {isCached} {lastUpdated} {isStale} />
					</span>
				{/if}
			</span>
		{/if}
	</TransitionWrapper>
{/if}

<style>
	.profit-loss-cell {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
	}

	.text-gray-400 {
		color: #9ca3af; /* Gray-400 */
		opacity: 0.7;
	}

	.text-loss {
		color: #ef4444; /* Red-500 */
	}

	.text-profit {
		color: #10b981; /* Emerald-500 */
	}

	.ml-1 {
		margin-left: 0.25rem;
	}

	.text-sm {
		font-size: 0.875rem;
	}
</style>
