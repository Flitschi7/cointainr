<script lang="ts">
	import type { Asset } from '$lib/types';
	import { formatPercentage, formatCurrency } from '$lib/utils/numberFormat';
	import * as enhancedApi from '$lib/services/enhancedApi';

	export let assets: Asset[] = [];

	export let assetPrices: Map<number, { price: number; currency: string }> = new Map();
	export let refreshTrigger: number = 0;

	interface RiskMetrics {
		overallScore: number;
		diversificationScore: number;
		concentrationRisk: number;
		trackingScore: number;
		riskLevel: 'Low' | 'Medium' | 'High';
		recommendations: string[];
	}

	let riskMetrics: RiskMetrics | null = null;

	function calculateRiskMetrics(): RiskMetrics {
		const totalAssets = assets.length;
		if (totalAssets === 0) {
			return {
				overallScore: 0,
				diversificationScore: 0,
				concentrationRisk: 100,
				trackingScore: 0,
				riskLevel: 'High',
				recommendations: ['Add assets to your portfolio to start risk analysis']
			};
		}

		// For sync fallback, use simple calculation without currency conversion
		const assetValues: { [id: number]: number } = {};
		let totalValue = 0;

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
			assetValues[asset.id] = value;
			totalValue += value;
		});

		return calculateRiskFromValues(assetValues, totalValue);
	}

	async function calculateRiskMetricsAsync(): Promise<RiskMetrics> {
		const targetCurrency = 'EUR';

		// Calculate asset values for concentration analysis with currency conversion
		const assetValues: { [id: number]: number } = {};
		let totalValue = 0;

		for (const asset of assets) {
			let value = 0;
			
			if (asset.type === 'cash') {
				value = asset.quantity;
			} else {
				const priceData = assetPrices.get(asset.id);
				
				if (priceData) {
					let currentValue = priceData.price * asset.quantity;
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
			assetValues[asset.id] = value;
			totalValue += value;
		}

		return calculateRiskFromValues(assetValues, totalValue);
	}

	function calculateRiskFromValues(assetValues: { [id: number]: number }, totalValue: number): RiskMetrics {

		// 1. Diversification Score (0-100)
		const assetTypes = new Set(assets.map(a => a.type));
		const brokers = new Set(assets.map(a => a.name));
		const currencies = new Set(assets.map(a => a.currency || 'USD'));
		
		// Base score from type diversity
		let diversificationScore = Math.min((assetTypes.size / 3) * 40, 40); // Max 40 for 3+ types
		// Add points for broker diversity
		diversificationScore += Math.min((brokers.size / 3) * 30, 30); // Max 30 for 3+ brokers
		// Add points for currency diversity
		diversificationScore += Math.min((currencies.size / 3) * 30, 30); // Max 30 for 3+ currencies

		// 2. Concentration Risk (0-100, lower is better)
		let concentrationRisk = 0;
		if (totalValue > 0) {
			const sortedValues = Object.values(assetValues).sort((a, b) => b - a);
			const top5Value = sortedValues.slice(0, 5).reduce((sum, val) => sum + val, 0);
			const top5Percentage = (top5Value / totalValue) * 100;
			
			// High concentration = high risk
			if (top5Percentage > 80) concentrationRisk = 90;
			else if (top5Percentage > 60) concentrationRisk = 70;
			else if (top5Percentage > 40) concentrationRisk = 50;
			else if (top5Percentage > 20) concentrationRisk = 30;
			else concentrationRisk = 10;
		}

		// 3. Tracking Score (how many assets have purchase prices)
		const trackedAssets = assets.filter(a => a.type !== 'cash' && a.purchase_price).length;
		const trackableAssets = assets.filter(a => a.type !== 'cash').length;
		const trackingScore = trackableAssets > 0 ? (trackedAssets / trackableAssets) * 100 : 100;

		// 4. Overall Score (weighted average)
		const overallScore = Math.round(
			(diversificationScore * 0.4) + 
			((100 - concentrationRisk) * 0.4) + 
			(trackingScore * 0.2)
		);

		// 5. Risk Level
		let riskLevel: 'Low' | 'Medium' | 'High';
		if (overallScore >= 70) riskLevel = 'Low';
		else if (overallScore >= 40) riskLevel = 'Medium';
		else riskLevel = 'High';

		// 6. Generate recommendations
		const recommendations: string[] = [];
		
		if (assetTypes.size < 3) {
			const allTypes: ('cash' | 'stock' | 'crypto' | 'derivative')[] = ['cash', 'stock', 'crypto', 'derivative'];
			const missing = allTypes.filter(type => !assetTypes.has(type));
			recommendations.push(`Consider adding ${missing.join(' and ')} to diversify asset types`);
		}
		
		if (brokers.size < 3) {
			recommendations.push('Spread investments across more brokers to reduce platform risk');
		}
		
		if (concentrationRisk > 70) {
			recommendations.push('High concentration detected - consider rebalancing your largest positions');
		}
		
		if (trackingScore < 80) {
			recommendations.push('Add purchase prices to more assets for better performance tracking');
		}
		
		if (recommendations.length === 0) {
			recommendations.push('Portfolio shows good risk management practices');
		}

		return {
			overallScore,
			diversificationScore,
			concentrationRisk,
			trackingScore,
			riskLevel,
			recommendations
		};
	}

	function getRiskColor(score: number): string {
		if (score >= 70) return 'text-profit';
		if (score >= 40) return 'text-amber-400';
		return 'text-loss';
	}

	function getRiskBgColor(score: number): string {
		if (score >= 70) return 'bg-profit';
		if (score >= 40) return 'bg-amber-400';
		return 'bg-loss';
	}

	// Reactive calculation
	$: if (assets && assetPrices && (refreshTrigger || refreshTrigger === 0)) {
		calculateRiskMetricsAsync().then(result => {
			riskMetrics = result;
		}).catch(error => {
			console.error('Error calculating risk metrics:', error);
			riskMetrics = calculateRiskMetrics(); // Fallback to sync version
		});
	}
</script>

<div class="w-full h-full">
	{#if !riskMetrics}
		<div class="flex items-center justify-center h-64 text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">🧠</div>
				<p>Analyzing portfolio risk...</p>
			</div>
		</div>
	{:else}
		<div class="space-y-6">
			<!-- Overall Risk Score -->
			<div class="text-center">
				<div class="inline-flex items-center justify-center w-24 h-24 rounded-full bg-surface border-4 {getRiskBgColor(riskMetrics.overallScore)} border-opacity-20">
					<div class="text-center">
						<div class="text-2xl font-bold {getRiskColor(riskMetrics.overallScore)}">
							{riskMetrics.overallScore}
						</div>
						<div class="text-xs text-gray-400">SCORE</div>
					</div>
				</div>
				<div class="mt-2">
					<h3 class="text-lg font-bold {getRiskColor(riskMetrics.overallScore)}">
						{riskMetrics.riskLevel} Risk
					</h3>
					<p class="text-sm text-gray-400">Portfolio Risk Assessment</p>
				</div>
			</div>

			<!-- Risk Metrics Grid -->
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
				<!-- Diversification -->
				<div class="bg-surface rounded-lg p-4">
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-gray-300">Diversification</span>
						<span class="text-lg font-bold {getRiskColor(riskMetrics.diversificationScore)}">
							{Math.round(riskMetrics.diversificationScore)}
						</span>
					</div>
					<div class="w-full bg-background rounded-full h-2">
						<div 
							class="h-2 rounded-full transition-all duration-500 {getRiskBgColor(riskMetrics.diversificationScore)}" 
							style="width: {riskMetrics.diversificationScore}%"
						></div>
					</div>
					<p class="text-xs text-gray-400 mt-1">Asset types, brokers & currencies</p>
				</div>

				<!-- Concentration Risk -->
				<div class="bg-surface rounded-lg p-4">
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-gray-300">Concentration</span>
						<span class="text-lg font-bold {getRiskColor(100 - riskMetrics.concentrationRisk)}">
							{Math.round(100 - riskMetrics.concentrationRisk)}
						</span>
					</div>
					<div class="w-full bg-background rounded-full h-2">
						<div 
							class="h-2 rounded-full transition-all duration-500 {getRiskBgColor(100 - riskMetrics.concentrationRisk)}" 
							style="width: {100 - riskMetrics.concentrationRisk}%"
						></div>
					</div>
					<p class="text-xs text-gray-400 mt-1">Position size distribution</p>
				</div>

				<!-- Tracking Coverage -->
				<div class="bg-surface rounded-lg p-4">
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-gray-300">Tracking</span>
						<span class="text-lg font-bold {getRiskColor(riskMetrics.trackingScore)}">
							{Math.round(riskMetrics.trackingScore)}
						</span>
					</div>
					<div class="w-full bg-background rounded-full h-2">
						<div 
							class="h-2 rounded-full transition-all duration-500 {getRiskBgColor(riskMetrics.trackingScore)}" 
							style="width: {riskMetrics.trackingScore}%"
						></div>
					</div>
					<p class="text-xs text-gray-400 mt-1">Performance monitoring coverage</p>
				</div>
			</div>

			<!-- Recommendations -->
			<div class="bg-surface rounded-lg p-4">
				<h4 class="font-semibold text-text-light mb-3 flex items-center gap-2">
					<span class="text-lg">💡</span>
					Risk Management Recommendations
				</h4>
				<ul class="space-y-2">
					{#each riskMetrics.recommendations as recommendation}
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
