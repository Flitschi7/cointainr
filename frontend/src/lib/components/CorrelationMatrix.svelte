<script lang="ts">
	import type { Asset } from '$lib/types';

	export let assets: Asset[] = [];

	export let assetPrices: Map<number, { price: number; currency: string }> = new Map();
	export let refreshTrigger: number = 0;

	interface CorrelationData {
		assets: { id: number; name: string; symbol: string }[];
		matrix: number[][];
		insights: string[];
	}

	let correlationData: CorrelationData | null = null;

	function calculateCorrelation(): CorrelationData {
		// Filter to only tradeable assets with symbols
		const tradeableAssets = assets.filter(a => 
			a.type !== 'cash' && 
			a.symbol && 
			assetPrices.has(a.id)
		);

		if (tradeableAssets.length < 2) {
			return {
				assets: [],
				matrix: [],
				insights: ['Need at least 2 tradeable assets to calculate correlations']
			};
		}

		// For demonstration, we'll create a simplified correlation matrix
		// In a real implementation, you'd calculate this from historical price data
		const assetInfo = tradeableAssets.map(asset => ({
			id: asset.id,
			name: asset.assetname || asset.symbol || 'Unknown',
			symbol: asset.symbol || ''
		}));

		// Simulate correlation matrix (normally you'd calculate from price history)
		const matrix: number[][] = [];
		const n = assetInfo.length;

		for (let i = 0; i < n; i++) {
			matrix[i] = [];
			for (let j = 0; j < n; j++) {
				if (i === j) {
					matrix[i][j] = 1.0; // Perfect correlation with itself
				} else {
					// Simulate correlations based on asset types
					const asset1 = tradeableAssets[i];
					const asset2 = tradeableAssets[j];
					
					if (asset1.type === asset2.type) {
						// Same asset type = higher correlation
						matrix[i][j] = 0.3 + Math.random() * 0.4; // 0.3 to 0.7
					} else {
						// Different asset types = lower correlation
						matrix[i][j] = -0.2 + Math.random() * 0.4; // -0.2 to 0.2
					}
					
					// Ensure symmetry
					if (j < i) {
						matrix[i][j] = matrix[j][i];
					}
				}
			}
		}

		// Generate insights
		const insights: string[] = [];
		
		// Find highly correlated pairs
		const highCorrelations: string[] = [];
		const lowCorrelations: string[] = [];
		
		for (let i = 0; i < n; i++) {
			for (let j = i + 1; j < n; j++) {
				const correlation = matrix[i][j];
				if (correlation > 0.7) {
					highCorrelations.push(`${assetInfo[i].symbol} & ${assetInfo[j].symbol}`);
				} else if (correlation < -0.3) {
					lowCorrelations.push(`${assetInfo[i].symbol} & ${assetInfo[j].symbol}`);
				}
			}
		}

		if (highCorrelations.length > 0) {
			insights.push(`High correlation detected: ${highCorrelations.slice(0, 3).join(', ')}`);
		}
		
		if (lowCorrelations.length > 0) {
			insights.push(`Good diversification between: ${lowCorrelations.slice(0, 3).join(', ')}`);
		}
		
		if (highCorrelations.length === 0 && lowCorrelations.length === 0) {
			insights.push('Moderate correlations - reasonable diversification');
		}

		// Portfolio-level insights
		const avgCorrelation = matrix.flat()
			.filter((val, idx, arr) => idx % (n + 1) !== 0) // Exclude diagonal (1.0 values)
			.reduce((sum, val) => sum + Math.abs(val), 0) / (n * n - n);
		
		if (avgCorrelation > 0.5) {
			insights.push('Portfolio shows high overall correlation - consider more diverse assets');
		} else if (avgCorrelation < 0.2) {
			insights.push('Excellent diversification - low average correlation between assets');
		}

		return {
			assets: assetInfo,
			matrix,
			insights
		};
	}

	function getCorrelationColor(value: number): string {
		if (value > 0.7) return 'bg-loss'; // High positive correlation = risk
		if (value > 0.3) return 'bg-amber-500';
		if (value > -0.3) return 'bg-gray-600';
		return 'bg-profit'; // Negative correlation = good for diversification
	}

	function getCorrelationTextColor(value: number): string {
		if (Math.abs(value) > 0.5) return 'text-white';
		return 'text-gray-300';
	}

	// Reactive calculation
	$: if (assets && assetPrices && (refreshTrigger || refreshTrigger === 0)) {
		correlationData = calculateCorrelation();
	}
</script>

<div class="w-full h-full">
	{#if !correlationData}
		<div class="flex items-center justify-center h-64 text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">📊</div>
				<p>Calculating correlations...</p>
			</div>
		</div>
	{:else if correlationData.assets.length === 0}
		<div class="flex items-center justify-center h-64 text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">🔗</div>
				<p>Need at least 2 tradeable assets</p>
				<p class="text-sm">Add stocks or crypto to see correlations</p>
			</div>
		</div>
	{:else}
		<div class="space-y-4">
			<!-- Correlation Matrix -->
			<div class="bg-surface rounded-lg p-4">
				<h4 class="font-semibold text-text-light mb-4 flex items-center gap-2">
					<span class="text-lg">🔗</span>
					Asset Correlation Matrix
				</h4>
				
				<div class="overflow-x-auto">
					<div class="inline-block min-w-full">
						<!-- Header Row -->
						<div class="grid gap-1 mb-1" style="grid-template-columns: 60px repeat({correlationData.assets.length}, 60px);">
							<div class="text-xs text-gray-400 p-1"></div>
							{#each correlationData.assets as asset}
								<div class="text-xs text-gray-400 p-1 text-center font-mono" title={asset.name}>
									{asset.symbol.slice(0, 4)}
								</div>
							{/each}
						</div>
						
						<!-- Matrix Rows -->
						{#each correlationData.matrix as row, i}
							<div class="grid gap-1 mb-1" style="grid-template-columns: 60px repeat({correlationData.assets.length}, 60px);">
								<!-- Row Label -->
								<div class="text-xs text-gray-400 p-1 text-right font-mono" title={correlationData.assets[i].name}>
									{correlationData.assets[i].symbol.slice(0, 4)}
								</div>
								
								<!-- Correlation Values -->
								{#each row as value, j}
									<div 
										class="text-xs p-1 text-center rounded transition-all duration-200 {getCorrelationColor(value)} {getCorrelationTextColor(value)}"
										title="{correlationData.assets[i].symbol} vs {correlationData.assets[j].symbol}: {value.toFixed(2)}"
									>
										{value.toFixed(2)}
									</div>
								{/each}
							</div>
						{/each}
					</div>
				</div>
				
				<!-- Legend -->
				<div class="mt-4 flex items-center justify-center gap-4 text-xs">
					<div class="flex items-center gap-1">
						<div class="w-3 h-3 bg-profit rounded"></div>
						<span class="text-gray-400">Diversified (-1 to -0.3)</span>
					</div>
					<div class="flex items-center gap-1">
						<div class="w-3 h-3 bg-gray-600 rounded"></div>
						<span class="text-gray-400">Neutral (-0.3 to 0.3)</span>
					</div>
					<div class="flex items-center gap-1">
						<div class="w-3 h-3 bg-amber-500 rounded"></div>
						<span class="text-gray-400">Moderate (0.3 to 0.7)</span>
					</div>
					<div class="flex items-center gap-1">
						<div class="w-3 h-3 bg-loss rounded"></div>
						<span class="text-gray-400">High Risk (0.7 to 1.0)</span>
					</div>
				</div>
			</div>

			<!-- Insights -->
			<div class="bg-surface rounded-lg p-4">
				<h4 class="font-semibold text-text-light mb-3 flex items-center gap-2">
					<span class="text-lg">💡</span>
					Correlation Insights
				</h4>
				<ul class="space-y-2">
					{#each correlationData.insights as insight}
						<li class="flex items-start gap-2 text-sm">
							<span class="text-primary mt-0.5">•</span>
							<span class="text-gray-300">{insight}</span>
						</li>
					{/each}
				</ul>
				
				<div class="mt-4 p-3 bg-background rounded border border-gray-600">
					<p class="text-xs text-gray-400">
						<strong>Note:</strong> This correlation matrix is simulated for demonstration. 
						In a production system, correlations would be calculated from historical price data over various timeframes.
					</p>
				</div>
			</div>
		</div>
	{/if}
</div>
