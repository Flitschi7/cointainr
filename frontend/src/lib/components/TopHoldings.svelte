<script lang="ts">
	import type { Asset } from '$lib/types';
	import { formatCurrency, formatPercentage } from '$lib/utils/numberFormat';

	export let assets: Asset[] = [];
	export let totalCurrency: string = 'EUR';
	export let assetPrices: Map<number, { price: number; currency: string }> = new Map();
	export let refreshTrigger: number = 0;
	export let maxHoldings: number = 10; // Show top 10 by default

	interface HoldingData {
		asset: Asset;
		value: number;
		percentage: number;
		displayName: string;
		type: string;
		broker: string;
		profitLoss?: number;
		profitLossPercentage?: number;
	}

	let topHoldings: HoldingData[] = [];
	let totalPortfolioValue = 0;

	function calculateTopHoldings() {
		const holdings: HoldingData[] = [];
		totalPortfolioValue = 0;

		// Calculate value for each asset
		assets.forEach(asset => {
			let value = 0;

			if (asset.type === 'cash') {
				value = asset.quantity;
			} else {
				const priceData = assetPrices.get(asset.id);
				if (priceData) {
					value = priceData.price * asset.quantity;
				}
			}

			totalPortfolioValue += value;

			// Calculate profit/loss if purchase price is available
			let profitLoss: number | undefined;
			let profitLossPercentage: number | undefined;

			if (asset.type !== 'cash' && asset.purchase_price && value > 0) {
				const totalPurchaseValue = asset.purchase_price * asset.quantity;
				profitLoss = value - totalPurchaseValue;
				profitLossPercentage = (profitLoss / totalPurchaseValue) * 100;
			}

			const holding: HoldingData = {
				asset,
				value,
				percentage: 0, // Will be calculated after we have total
				displayName: asset.assetname || asset.symbol || asset.name || 'Unknown',
				type: asset.type,
				broker: asset.name || 'Unknown Broker',
				profitLoss,
				profitLossPercentage
			};

			holdings.push(holding);
		});

		// Calculate percentages and sort by value (descending)
		holdings.forEach(holding => {
			holding.percentage = totalPortfolioValue > 0 ? (holding.value / totalPortfolioValue) * 100 : 0;
		});

		// Sort by value (largest first) and take top N
		topHoldings = holdings
			.sort((a, b) => b.value - a.value)
			.slice(0, maxHoldings)
			.filter(holding => holding.value > 0);
	}

	// Get icon for asset type
	function getTypeIcon(type: string): string {
		switch (type) {
			case 'cash': return '💰';
			case 'stock': return '📈';
			case 'crypto': return '₿';
			case 'derivative': return '💸';
			default: return '❓';
		}
	}

	// Get color class for profit/loss
	function getProfitLossClass(value: number): string {
		if (value > 0) return 'text-profit';
		if (value < 0) return 'text-loss';
		return 'text-gray-400';
	}

	// Reactive calculation when data changes
	$: if (assets && assetPrices && (refreshTrigger || refreshTrigger === 0)) {
		calculateTopHoldings();
	}
</script>

<div class="w-full h-64 overflow-hidden">
	{#if assets.length === 0}
		<div class="flex items-center justify-center h-full text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">🏆</div>
				<p>No assets to display</p>
			</div>
		</div>
	{:else if topHoldings.length === 0}
		<div class="flex items-center justify-center h-full text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">🏆</div>
				<p>No holdings with value</p>
			</div>
		</div>
	{:else}
		<div class="h-full overflow-y-auto">
			<div class="space-y-2">
				{#each topHoldings as holding, index}
					<div class="bg-surface rounded-lg p-3 border border-gray-600 hover:border-gray-500 transition-colors">
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-3 flex-1 min-w-0">
								<!-- Rank and Type Icon -->
								<div class="flex items-center space-x-2 flex-shrink-0">
									<span class="text-gold font-bold text-sm w-6 text-center">#{index + 1}</span>
									<span class="text-lg">{getTypeIcon(holding.type)}</span>
								</div>
								
								<!-- Asset Info -->
								<div class="flex-1 min-w-0">
									<div class="flex items-center space-x-2">
										<h4 class="font-semibold text-text-light truncate text-sm">
											{holding.displayName}
										</h4>
										<span class="text-xs text-gray-400 uppercase font-mono">
											{holding.type}
										</span>
									</div>
									<p class="text-xs text-gray-400 truncate">
										{holding.broker}
									</p>
								</div>
							</div>
							
							<!-- Value and Performance -->
							<div class="text-right flex-shrink-0 ml-2">
								<div class="font-bold text-sm text-text-light">
									{formatCurrency(holding.value, totalCurrency)}
								</div>
								<div class="text-xs text-gray-400">
									{formatPercentage(holding.percentage)} of portfolio
								</div>
								{#if holding.profitLoss !== undefined && holding.profitLossPercentage !== undefined}
									<div class="text-xs {getProfitLossClass(holding.profitLoss)}">
										{holding.profitLoss >= 0 ? '+' : ''}{formatCurrency(holding.profitLoss, totalCurrency)}
										({holding.profitLossPercentage >= 0 ? '+' : ''}{formatPercentage(holding.profitLossPercentage)})
									</div>
								{/if}
							</div>
						</div>
						
						<!-- Progress Bar for Portfolio Percentage -->
						<div class="mt-2">
							<div class="w-full bg-background rounded-full h-1.5">
								<div 
									class="bg-gradient-to-r from-primary to-gold h-1.5 rounded-full transition-all duration-300" 
									style="width: {Math.min(holding.percentage, 100)}%"
								></div>
							</div>
						</div>
					</div>
				{/each}
			</div>
			
			{#if topHoldings.length === maxHoldings && assets.length > maxHoldings}
				<div class="mt-3 text-center text-xs text-gray-400">
					Showing top {maxHoldings} of {assets.length} assets
				</div>
			{/if}
		</div>
	{/if}
</div>
