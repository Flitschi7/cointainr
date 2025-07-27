<script lang="ts">
	import type { Asset } from '$lib/types';
	import * as enhancedApi from '$lib/services/enhancedApi';

	export let assets: Asset[] = [];
	export let assetPrices: Map<number, { price: number; currency: string }> = new Map();
	export let refreshTrigger: number = 0;

	interface EfficiencyMetrics {
		sharpeRatio: number;
		diversificationRatio: number;
		concentrationIndex: number;
		balanceScore: number;
		overallScore: number;
		recommendations: string[];
		details: {
			totalValue: number;
			assetCount: number;
			typeDistribution: { [key: string]: number };
			topHolding: { name: string; percentage: number };
		};
	}

	let efficiencyData: EfficiencyMetrics | null = null;

	function calculateEfficiency(): EfficiencyMetrics {
		if (assets.length === 0) {
			return {
				sharpeRatio: 0,
				diversificationRatio: 0,
				concentrationIndex: 0,
				balanceScore: 0,
				overallScore: 0,
				recommendations: ['Add assets to your portfolio to begin efficiency analysis'],
				details: {
					totalValue: 0,
					assetCount: 0,
					typeDistribution: {},
					topHolding: { name: 'None', percentage: 0 }
				}
			};
		}

		// For sync fallback, use simple calculation without currency conversion
		let totalValue = 0;
		const assetValues: { asset: Asset; value: number; type: string }[] = [];

		assets.forEach(asset => {
			let value = 0;
			if (asset.type === 'cash') {
				value = asset.quantity || 0;
			} else {
				const priceData = assetPrices.get(asset.id);
				if (priceData) {
					value = (asset.quantity || 0) * priceData.price;
				}
			}
			totalValue += value;
			assetValues.push({ asset, value, type: asset.type });
		});

		return calculateEfficiencyFromValues(assetValues, totalValue);
	}

	async function calculateEfficiencyAsync(): Promise<EfficiencyMetrics> {
		const targetCurrency = 'EUR';

		// Calculate total portfolio value with currency conversion
		let totalValue = 0;
		const assetValues: { asset: Asset; value: number; type: string }[] = [];

		for (const asset of assets) {
			let value = 0;
			
			if (asset.type === 'cash') {
				value = asset.quantity || 0;
			} else {
				const priceData = assetPrices.get(asset.id);
				
				if (priceData) {
					let currentValue = (asset.quantity || 0) * priceData.price;
					const priceCurrency = priceData.currency;

					// Convert to target currency if needed
					if (priceCurrency !== targetCurrency) {
						try {
							const conversionData = await enhancedApi.convertCurrency(
								priceCurrency,
								targetCurrency,
								currentValue,
								{ forceRefresh: false }
							);
							currentValue = conversionData.converted;
						} catch (error) {
							console.error(`Failed to convert ${priceCurrency} to ${targetCurrency}:`, error);
						}
					}

					value = currentValue;
				}
			}
			totalValue += value;
			assetValues.push({ asset, value, type: asset.type });
		}

		return calculateEfficiencyFromValues(assetValues, totalValue);
	}

	function calculateEfficiencyFromValues(assetValues: { asset: Asset; value: number; type: string }[], totalValue: number): EfficiencyMetrics {
		if (totalValue === 0) {
			return {
				sharpeRatio: 0,
				diversificationRatio: 0,
				concentrationIndex: 0,
				balanceScore: 0,
				overallScore: 0,
				recommendations: ['Portfolio value is zero - add asset quantities and prices'],
				details: {
					totalValue: 0,
					assetCount: assets.length,
					typeDistribution: {},
					topHolding: { name: 'None', percentage: 0 }
				}
			};
		}

		// Calculate asset type distribution
		const typeDistribution: { [key: string]: number } = {};
		assetValues.forEach(({ type, value }) => {
			typeDistribution[type] = (typeDistribution[type] || 0) + value;
		});

		// Convert to percentages
		Object.keys(typeDistribution).forEach(type => {
			typeDistribution[type] = (typeDistribution[type] / totalValue) * 100;
		});

		// Find top holding
		const sortedAssets = assetValues.sort((a, b) => b.value - a.value);
		const topHolding = sortedAssets[0];
		const topHoldingPercentage = (topHolding.value / totalValue) * 100;

		// 1. Sharpe Ratio (simplified - using risk/return estimate)
		const sharpeRatio = calculateSharpeRatio(assetValues, totalValue);

		// 2. Diversification Ratio (based on number of assets and distribution)
		const diversificationRatio = calculateDiversificationRatio(assetValues, totalValue);

		// 3. Concentration Index (Herfindahl-Hirschman Index)
		const concentrationIndex = calculateConcentrationIndex(assetValues, totalValue);

		// 4. Balance Score (based on asset type distribution)
		const balanceScore = calculateBalanceScore(typeDistribution);

		// 5. Overall Efficiency Score (weighted average)
		const overallScore = (
			sharpeRatio * 0.3 +
			diversificationRatio * 0.25 +
			(100 - concentrationIndex) * 0.25 +
			balanceScore * 0.2
		);

		// Generate recommendations
		const recommendations = generateRecommendations(
			sharpeRatio,
			diversificationRatio,
			concentrationIndex,
			balanceScore,
			typeDistribution,
			topHoldingPercentage,
			assetValues.length
		);

		return {
			sharpeRatio,
			diversificationRatio,
			concentrationIndex,
			balanceScore,
			overallScore,
			recommendations,
			details: {
				totalValue,
				assetCount: assets.length,
				typeDistribution,
				topHolding: {
					name: topHolding.asset.assetname || topHolding.asset.symbol || 'Unknown',
					percentage: topHoldingPercentage
				}
			}
		};
	}

	function calculateSharpeRatio(assetValues: any[], totalValue: number): number {
		// Simplified Sharpe ratio based on asset type risk assumptions
		let weightedRisk = 0;
		let weightedReturn = 0;

		assetValues.forEach(({ type, value }) => {
			const weight = value / totalValue;
			
			// Risk assumptions (standard deviation %)
			const riskByType: { [key: string]: number } = {
				'cash': 1,
				'stock': 15,
				'crypto': 50,
				'derivative': 25  // Derivatives typically have moderate to high risk
			};
			
			// Expected return assumptions (%)
			const returnByType: { [key: string]: number } = {
				'cash': 2,
				'stock': 8,
				'crypto': 15,
				'derivative': 10  // Derivatives can offer good returns but vary widely
			};

			weightedRisk += weight * (riskByType[type] || 10);
			weightedReturn += weight * (returnByType[type] || 5);
		});

		// Sharpe ratio = (return - risk-free rate) / risk
		const riskFreeRate = 2; // 2% risk-free rate
		const sharpe = (weightedReturn - riskFreeRate) / weightedRisk;
		
		// Convert to 0-100 scale
		return Math.max(0, Math.min(100, sharpe * 20 + 50));
	}

	function calculateDiversificationRatio(assetValues: any[], totalValue: number): number {
		// Based on number of assets and how evenly distributed they are
		const assetCount = assetValues.length;
		
		// Ideal distribution would be equal weights
		const idealWeight = 1 / assetCount;
		let sumSquaredDeviations = 0;

		assetValues.forEach(({ value }) => {
			const actualWeight = value / totalValue;
			const deviation = actualWeight - idealWeight;
			sumSquaredDeviations += deviation * deviation;
		});

		// Lower deviation = better diversification
		const diversificationScore = 1 - Math.sqrt(sumSquaredDeviations);
		
		// Bonus for having more assets (up to 20)
		const assetBonus = Math.min(assetCount / 20, 1) * 0.3;
		
		return Math.max(0, Math.min(100, (diversificationScore + assetBonus) * 100));
	}

	function calculateConcentrationIndex(assetValues: any[], totalValue: number): number {
		// Herfindahl-Hirschman Index (0-100, lower is better)
		let hhi = 0;
		
		assetValues.forEach(({ value }) => {
			const marketShare = (value / totalValue) * 100;
			hhi += marketShare * marketShare;
		});

		return Math.min(100, hhi / 100); // Normalize to 0-100
	}

	function calculateBalanceScore(typeDistribution: { [key: string]: number }): number {
		const types = Object.keys(typeDistribution);
		
		// Ideal would be roughly equal distribution across asset types
		if (types.length === 1) return 30; // Single asset type = poor balance
		if (types.length === 2) return 60; // Two types = decent
		if (types.length >= 3) {
			// Check if distribution is reasonable (no type over 80%)
			const maxPercentage = Math.max(...Object.values(typeDistribution));
			if (maxPercentage > 80) return 40;
			if (maxPercentage > 60) return 70;
			return 90; // Well balanced
		}
		
		return 50;
	}

	function generateRecommendations(
		sharpe: number,
		diversification: number,
		concentration: number,
		balance: number,
		typeDistribution: { [key: string]: number },
		topHoldingPercentage: number,
		assetCount: number
	): string[] {
		const recommendations: string[] = [];

		// Concentration recommendations
		if (concentration > 70) {
			recommendations.push('High concentration risk - consider reducing largest positions');
		}
		if (topHoldingPercentage > 40) {
			recommendations.push(`Top holding (${topHoldingPercentage.toFixed(1)}%) is very large - consider rebalancing`);
		}

		// Diversification recommendations
		if (diversification < 40) {
			recommendations.push('Low diversification - consider adding more assets');
		}
		if (assetCount < 5) {
			recommendations.push('Consider adding more assets for better diversification');
		}

		// Asset type balance recommendations
		const cashPercentage = typeDistribution['cash'] || 0;
		const cryptoPercentage = typeDistribution['crypto'] || 0;

		if (cashPercentage > 50) {
			recommendations.push('High cash allocation - consider investing for better returns');
		}
		if (cryptoPercentage > 30) {
			recommendations.push('High crypto allocation - consider the volatility risk');
		}
		if (!typeDistribution['stock']) {
			recommendations.push('Consider adding stocks for stable long-term growth');
		}

		// Risk-adjusted return recommendations
		if (sharpe < 40) {
			recommendations.push('Low risk-adjusted returns - review asset allocation');
		}

		// Overall efficiency
		const overall = (sharpe + diversification + (100 - concentration) + balance) / 4;
		if (overall > 80) {
			recommendations.push('Excellent portfolio efficiency - maintain current strategy');
		} else if (overall < 50) {
			recommendations.push('Portfolio needs improvement - focus on diversification and balance');
		}

		return recommendations.length > 0 ? recommendations : ['Portfolio analysis complete - no major issues detected'];
	}

	function getScoreColor(score: number): string {
		if (score >= 80) return 'text-profit';
		if (score >= 60) return 'text-amber-400';
		if (score >= 40) return 'text-orange-400';
		return 'text-loss';
	}

	function getScoreBackground(score: number): string {
		if (score >= 80) return 'bg-profit';
		if (score >= 60) return 'bg-amber-400';
		if (score >= 40) return 'bg-orange-400';
		return 'bg-loss';
	}

	// Reactive calculation
	$: if (assets && assetPrices && (refreshTrigger || refreshTrigger === 0)) {
		calculateEfficiencyAsync().then(result => {
			efficiencyData = result;
		}).catch(error => {
			console.error('Error calculating efficiency:', error);
			efficiencyData = calculateEfficiency(); // Fallback to sync version
		});
	}
</script>

<div class="w-full h-full">
	{#if !efficiencyData}
		<div class="flex items-center justify-center h-64 text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">⚡</div>
				<p>Calculating efficiency...</p>
			</div>
		</div>
	{:else}
		<div class="space-y-4">
			<!-- Overall Score -->
			<div class="bg-surface rounded-lg p-4">
				<h4 class="font-semibold text-text-light mb-4 flex items-center gap-2">
					<span class="text-lg">⚡</span>
					Portfolio Efficiency Score
				</h4>
				
				<div class="text-center mb-4">
					<div class="text-3xl font-bold {getScoreColor(efficiencyData.overallScore)} mb-2">
						{efficiencyData.overallScore.toFixed(1)}
					</div>
					<div class="text-sm text-gray-400">Overall Efficiency Score</div>
				</div>

				<!-- Score Breakdown -->
				<div class="grid grid-cols-2 gap-4">
					<div class="text-center">
						<div class="text-xl font-semibold {getScoreColor(efficiencyData.sharpeRatio)}">
							{efficiencyData.sharpeRatio.toFixed(1)}
						</div>
						<div class="text-xs text-gray-400">Risk-Adjusted Returns</div>
					</div>
					<div class="text-center">
						<div class="text-xl font-semibold {getScoreColor(efficiencyData.diversificationRatio)}">
							{efficiencyData.diversificationRatio.toFixed(1)}
						</div>
						<div class="text-xs text-gray-400">Diversification</div>
					</div>
					<div class="text-center">
						<div class="text-xl font-semibold {getScoreColor(100 - efficiencyData.concentrationIndex)}">
							{(100 - efficiencyData.concentrationIndex).toFixed(1)}
						</div>
						<div class="text-xs text-gray-400">Distribution</div>
					</div>
					<div class="text-center">
						<div class="text-xl font-semibold {getScoreColor(efficiencyData.balanceScore)}">
							{efficiencyData.balanceScore.toFixed(1)}
						</div>
						<div class="text-xs text-gray-400">Type Balance</div>
					</div>
				</div>

				<!-- Progress Bar -->
				<div class="mt-4">
					<div class="w-full bg-gray-700 rounded-full h-2">
						<div 
							class="h-2 rounded-full transition-all duration-500 {getScoreBackground(efficiencyData.overallScore)}"
							style="width: {efficiencyData.overallScore}%"
						></div>
					</div>
				</div>
			</div>

			<!-- Portfolio Details -->
			<div class="bg-surface rounded-lg p-4">
				<h4 class="font-semibold text-text-light mb-3 flex items-center gap-2">
					<span class="text-lg">📊</span>
					Portfolio Structure
				</h4>
				
				<div class="grid grid-cols-2 gap-4">
					<div>
						<div class="text-sm text-gray-400">Total Value</div>
						<div class="text-lg font-semibold text-text-light">
							€{efficiencyData.details.totalValue.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-400">Assets</div>
						<div class="text-lg font-semibold text-text-light">
							{efficiencyData.details.assetCount}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-400">Largest Holding</div>
						<div class="text-lg font-semibold text-text-light truncate">
							{efficiencyData.details.topHolding.name}
						</div>
						<div class="text-xs text-gray-400">
							{efficiencyData.details.topHolding.percentage.toFixed(1)}% of portfolio
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-400">Asset Types</div>
						<div class="text-sm">
							{#each Object.entries(efficiencyData.details.typeDistribution) as [type, percentage]}
								<div class="flex justify-between">
									<span class="capitalize text-gray-300">{type}:</span>
									<span class="text-text-light">{percentage.toFixed(1)}%</span>
								</div>
							{/each}
						</div>
					</div>
				</div>
			</div>

			<!-- Recommendations -->
			<div class="bg-surface rounded-lg p-4">
				<h4 class="font-semibold text-text-light mb-3 flex items-center gap-2">
					<span class="text-lg">💡</span>
					Efficiency Recommendations
				</h4>
				<ul class="space-y-2">
					{#each efficiencyData.recommendations as recommendation}
						<li class="flex items-start gap-2 text-sm">
							<span class="text-primary mt-0.5">•</span>
							<span class="text-gray-300">{recommendation}</span>
						</li>
					{/each}
				</ul>
			</div>

		</div>
	{/if}
</div>
