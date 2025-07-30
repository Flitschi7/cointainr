<script lang="ts">
	/**
	 * Compact Currency Rate Display
	 *
	 * Shows only the relevant currency rates for the selected base currency
	 * Positioned inline next to the currency selector
	 */
	import * as enhancedApi from '$lib/services/enhancedApi';
	import { devLog } from '$lib/utils/logger';

	export let baseCurrency: string = 'EUR'; // The currency everything is converted to
	export let assets: any[] = []; // Assets to determine which currencies are relevant

	// Get unique currencies from assets that are different from base currency
	$: relevantCurrencies = [
		...new Set(
			assets
				.map((asset) => {
					// For cash assets, use the currency field
					if (asset.type === 'cash') {
						return asset.currency || 'USD';
					}
					// For stocks/crypto, use buy_currency first, then currency, then default to USD
					return asset.buy_currency || asset.currency || 'USD';
				})
				.filter((currency) => currency && currency !== baseCurrency)
		)
	];

	// Debug logging
	$: if (assets.length > 0) {
		devLog.debug('CurrencyRateDisplay - Assets:', assets.length);
		devLog.debug('CurrencyRateDisplay - Base currency:', baseCurrency);
		devLog.debug(
			'CurrencyRateDisplay - Asset currencies:',
			assets.map((asset) => {
				const detectedCurrency =
					asset.type === 'cash'
						? asset.currency || 'USD'
						: asset.buy_currency || asset.currency || 'USD';
				return {
					name: asset.name,
					type: asset.type,
					currency: asset.currency,
					buy_currency: asset.buy_currency,
					detected: detectedCurrency
				};
			})
		);
		devLog.debug('CurrencyRateDisplay - Relevant currencies:', relevantCurrencies);
	}

	let currencyRates: Map<string, { rate: number; cached: boolean }> = new Map();
	let isRefreshing = false;
	let lastRefreshTime: Date | null = null;

	// Load currency rates for relevant currencies only
	async function loadRelevantRates() {
		if (relevantCurrencies.length === 0) return;

		try {
			const ratePromises = relevantCurrencies.map(async (currency) => {
				try {
					const rateData = await enhancedApi.getConversionRate(currency, baseCurrency);

					// Calculate if data is stale (older than 24 hours)
					const fetchedAt = rateData.fetched_at ? new Date(rateData.fetched_at) : new Date();
					const now = new Date();
					const ageInHours = (now.getTime() - fetchedAt.getTime()) / (1000 * 60 * 60);
					const isStale = ageInHours > 24;

					return {
						currency,
						rate: rateData.rate,
						isStale: isStale,
						ageInHours: ageInHours
					};
				} catch (error) {
					console.error(`Failed to load rate for ${currency}:`, error);
					return null;
				}
			});

			const rates = await Promise.all(ratePromises);

			// Update the rates map
			currencyRates.clear();
			rates.forEach((rateInfo) => {
				if (rateInfo) {
					currencyRates.set(rateInfo.currency, {
						rate: rateInfo.rate,
						isStale: rateInfo.isStale,
						ageInHours: rateInfo.ageInHours
					});
				}
			});

			// Trigger reactivity
			currencyRates = currencyRates;
		} catch (error) {
			console.error('Failed to load currency rates:', error);
		}
	}

	// Refresh all relevant currency rates (force refresh)
	async function refreshRates() {
		if (isRefreshing || relevantCurrencies.length === 0) return;

		isRefreshing = true;

		try {
			const ratePromises = relevantCurrencies.map(async (currency) => {
				try {
					const rateData = await enhancedApi.getConversionRate(currency, baseCurrency, {
						forceRefresh: true
					});

					// Fresh data is never stale
					return {
						currency,
						rate: rateData.rate,
						isStale: false,
						ageInHours: 0
					};
				} catch (error) {
					console.error(`Failed to refresh rate for ${currency}:`, error);
					return null;
				}
			});

			const rates = await Promise.all(ratePromises);

			// Update the rates map
			currencyRates.clear();
			rates.forEach((rateInfo) => {
				if (rateInfo) {
					currencyRates.set(rateInfo.currency, {
						rate: rateInfo.rate,
						isStale: rateInfo.isStale,
						ageInHours: rateInfo.ageInHours
					});
				}
			});

			// Trigger reactivity
			currencyRates = currencyRates;
			lastRefreshTime = new Date();
		} catch (error) {
			console.error('Failed to refresh currency rates:', error);
		} finally {
			isRefreshing = false;
		}
	}

	// Load rates when component mounts or when relevant currencies change
	$: if (relevantCurrencies.length > 0) {
		loadRelevantRates();
	}
</script>

<div
	class="bg-surface text-text-light flex items-center gap-2 rounded-lg border border-gray-600 px-3 py-2 text-sm"
>
	{#if relevantCurrencies.length > 0}
		<div class="flex items-center gap-3">
			{#each Array.from(currencyRates.entries()) as [currency, rateInfo]}
				<div class="flex items-center gap-1">
					<span class="font-medium text-gray-400">{currency}→{baseCurrency}:</span>
					<span class="text-primary font-mono font-semibold">{rateInfo.rate.toFixed(4)}</span>
					<span
						class="text-xs"
						class:text-green-400={!rateInfo.isStale}
						class:text-red-400={rateInfo.isStale}
						title={rateInfo.isStale
							? `Stale exchange rate (${Math.round(rateInfo.ageInHours)}h old)`
							: `Fresh exchange rate (${Math.round(rateInfo.ageInHours)}h old)`}
					>
						●
					</span>
				</div>
			{/each}
		</div>

		<button
			class="hover:bg-background flex items-center justify-center rounded border border-gray-600 p-1 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
			on:click={refreshRates}
			disabled={isRefreshing}
			title="Refresh currency rates"
			aria-label="Refresh currency rates"
		>
			<svg
				class="h-3 w-3"
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
				/>
			</svg>
		</button>
	{:else}
		<span class="text-gray-400">
			{#if assets.length === 0}
				Loading rates...
			{:else}
				All assets in {baseCurrency}
			{/if}
		</span>
	{/if}
</div>
