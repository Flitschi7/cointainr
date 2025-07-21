<script lang="ts">
	/**
	 * Compact Currency Rate Display
	 *
	 * Shows only the relevant currency rates for the selected base currency
	 * Positioned inline next to the currency selector
	 */
	import * as enhancedApi from '$lib/services/enhancedApi';

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
		console.log('CurrencyRateDisplay - Assets:', assets.length);
		console.log('CurrencyRateDisplay - Base currency:', baseCurrency);
		console.log(
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
		console.log('CurrencyRateDisplay - Relevant currencies:', relevantCurrencies);
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
					return {
						currency,
						rate: rateData.rate,
						cached: rateData.cached || false
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
						cached: rateInfo.cached
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
					return {
						currency,
						rate: rateData.rate,
						cached: false // Fresh data
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
						cached: rateInfo.cached
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

<!-- Always show the component for debugging -->
<div class="currency-rates-compact">
	{#if relevantCurrencies.length > 0}
		<div class="rates-list">
			{#each Array.from(currencyRates.entries()) as [currency, rateInfo]}
				<div class="rate-item">
					<span class="currency-pair">{currency}→{baseCurrency}</span>
					<span class="rate-value">{rateInfo.rate.toFixed(4)}</span>
					<span class="cache-indicator" class:cached={rateInfo.cached}>
						{rateInfo.cached ? '📦' : '🟢'}
					</span>
				</div>
			{/each}
		</div>

		<button
			class="refresh-btn"
			on:click={refreshRates}
			disabled={isRefreshing}
			title="Refresh currency rates"
			aria-label="Refresh currency rates"
		>
			<svg
				class="icon"
				class:spinning={isRefreshing}
				viewBox="0 0 16 16"
				fill="none"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M3 3v4h.582m10.356 2A6.001 6.001 0 003.582 7m0 0H7m7 7v-4h-.581m0 0a6.003 6.003 0 01-10.357-2m10.357 2H10"
				/>
			</svg>
		</button>
	{:else}
		<div class="no-rates">
			<span class="text-sm text-gray-400">
				{#if assets.length === 0}
					Loading...
				{:else}
					All assets in {baseCurrency}
					{#if assets.length > 0}
						<span class="text-xs opacity-75">
							({assets.length} asset{assets.length !== 1 ? 's' : ''})
						</span>
					{/if}
				{/if}
			</span>
		</div>
	{/if}
</div>

<style>
	.currency-rates-compact {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem;
		background-color: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 0.25rem;
		font-size: 0.75rem;
	}

	.rates-list {
		display: flex;
		gap: 0.75rem;
	}

	.rate-item {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.currency-pair {
		color: #9ca3af;
		font-weight: 500;
	}

	.rate-value {
		font-family: 'JetBrains Mono', monospace;
		font-weight: 600;
		color: #10b981;
	}

	.cache-indicator {
		font-size: 0.7rem;
	}

	.cached {
		opacity: 0.7;
	}

	.refresh-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.25rem;
		background-color: transparent;
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 0.25rem;
		color: #9ca3af;
		cursor: pointer;
		transition: all 0.2s;
	}

	.refresh-btn:hover:not(:disabled) {
		background-color: rgba(255, 255, 255, 0.1);
		color: #f3f4f6;
	}

	.refresh-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.icon {
		width: 12px;
		height: 12px;
	}

	.spinning {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.no-rates {
		padding: 0.25rem 0.5rem;
	}
</style>
