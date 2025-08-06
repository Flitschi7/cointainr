<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, type ChartConfiguration } from 'chart.js/auto';
	import type { Asset } from '$lib/types';
	import { formatCurrency, formatPercentage } from '$lib/utils/numberFormat';

	export let assets: Asset[] = [];
	export let totalCurrency: string = 'EUR';
	export let assetPrices: Map<number, { price: number; currency: string }> = new Map();
	export let refreshTrigger: number = 0;

	let chartCanvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	interface AssetPerformance {
		name: string;
		profitLoss: number;
		profitLossPercentage: number;
		currentValue: number;
		purchaseValue: number;
		hasData: boolean;
	}

	// Calculate asset performance data
	function calculateAssetPerformance(): AssetPerformance[] {
		const performanceData: AssetPerformance[] = [];

		assets.forEach(asset => {

			// Skip cash assets as they don't have performance
			if (asset.type === 'cash') {
			}
			
			// Skip assets without purchase price
			if (!asset.purchase_price) {
				console.log(`[DEBUG] Skipping asset without purchase price: ${asset.symbol}`);
				return;
			}

			const priceData = assetPrices.get(asset.id);
			console.log(`[DEBUG] Price data for asset ${asset.symbol} (ID: ${asset.id}):`, priceData);
			
			if (!priceData) {
				console.log(`[DEBUG] No price data found for asset: ${asset.symbol}`);
				return;
			}

			const currentValue = priceData.price * asset.quantity;
			const purchaseValue = asset.purchase_price * asset.quantity;
			const profitLoss = currentValue - purchaseValue;
			const profitLossPercentage = (profitLoss / purchaseValue) * 100;

			const displayName = asset.assetname || asset.symbol || asset.name || 'Unknown';

			performanceData.push({
				name: displayName,
				profitLoss,
				profitLossPercentage,
				currentValue,
				purchaseValue,
				hasData: true
			});
		});

		// Sort by profit/loss amount (largest losses first, then largest gains)
		return performanceData.sort((a, b) => a.profitLoss - b.profitLoss);
	}

	function createChart() {
		if (!chartCanvas) return;

		const performanceData = calculateAssetPerformance();

		// Only show chart if there's data
		if (performanceData.length === 0) return;

		const labels = performanceData.map(item => {
			// Truncate long asset names for better display
			return item.name.length > 20 ? item.name.substring(0, 20) + '...' : item.name;
		});
		
		const profitLossData = performanceData.map(item => item.profitLoss);
		
		// Create colors: red for losses, green for gains
		const colors = performanceData.map(item => {
			if (item.profitLoss > 0) return '#10B981'; // Profit green
			if (item.profitLoss < 0) return '#EF4444'; // Loss red
			return '#6B7280'; // Neutral gray for break-even
		});

		const config: ChartConfiguration = {
			type: 'bar',
			data: {
				labels,
				datasets: [{
					label: `Profit/Loss (${totalCurrency})`,
					data: profitLossData,
					backgroundColor: colors,
					borderColor: colors,
					borderWidth: 1
				}]
			},
			options: {
				indexAxis: 'y' as const, // Horizontal bar chart
				responsive: true,
				maintainAspectRatio: false, // Allow flexible height
				plugins: {
					legend: {
						display: false // Hide legend for cleaner look
					},
					tooltip: {
						backgroundColor: '#1E1E2F',
						titleColor: '#F0F4F8',
						bodyColor: '#F0F4F8',
						borderColor: '#D4AF37',
						borderWidth: 1,
						titleFont: {
							size: 14,
							weight: 'bold'
						},
						bodyFont: {
							size: 13
						},
						callbacks: {
							title: function(context) {
								const index = context[0].dataIndex;
								return performanceData[index].name; // Show full name in tooltip
							},
							label: function(context) {
								const index = context.dataIndex;
								const item = performanceData[index];
								const value = context.parsed.x;
								const percentage = item.profitLossPercentage;
								
								return [
									`P&L: ${formatCurrency(value, totalCurrency)}`,
									`Percentage: ${formatPercentage(percentage)}`,
									`Current: ${formatCurrency(item.currentValue, totalCurrency)}`,
									`Purchase: ${formatCurrency(item.purchaseValue, totalCurrency)}`
								];
							}
						}
					}
				},
				scales: {
					x: {
						ticks: {
							color: '#F0F4F8',
							callback: function(value) {
								return formatCurrency(Number(value), totalCurrency);
							}
						},
						grid: {
							color: 'rgba(240, 244, 248, 0.1)'
						},
						title: {
							display: true,
							text: `Profit/Loss (${totalCurrency})`,
							color: '#F0F4F8',
							font: {
								size: 12,
								weight: 'bold'
							}
						}
					},
					y: {
						ticks: {
							color: '#F0F4F8',
							font: {
								size: 11
							}
						},
						grid: {
							display: false // Hide horizontal grid lines for cleaner look
						}
					}
				},
				elements: {
					bar: {
						borderRadius: 4 // Rounded corners for bars
					}
				}
			}
		};

		// Destroy existing chart if it exists
		if (chart) {
			chart.destroy();
		}

		chart = new Chart(chartCanvas, config);
	}

	onMount(() => {
		createChart();
	});

	onDestroy(() => {
		if (chart) {
			chart.destroy();
		}
	});

	// Reactive update when data changes
	$: if (chartCanvas && (assets || assetPrices || totalCurrency || refreshTrigger)) {
		createChart();
	}

	// Calculate summary stats for display
	$: performanceData = calculateAssetPerformance();
	$: totalGains = performanceData.filter(item => item.profitLoss > 0).reduce((sum, item) => sum + item.profitLoss, 0);
	$: totalLosses = performanceData.filter(item => item.profitLoss < 0).reduce((sum, item) => sum + item.profitLoss, 0);
	$: winnersCount = performanceData.filter(item => item.profitLoss > 0).length;
	$: losersCount = performanceData.filter(item => item.profitLoss < 0).length;
</script>

<div class="w-full h-64 flex flex-col">
	{#if assets.length === 0}
		<div class="flex items-center justify-center h-full text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">📊</div>
				<p>No assets to display</p>
			</div>
		</div>
	{:else if performanceData.length === 0}
		<div class="flex items-center justify-center h-full text-center text-gray-400">
			<div>
				<div class="text-4xl mb-2">📈</div>
				<p>No performance data available</p>
				<p class="text-sm">Assets need purchase prices to show performance</p>
			</div>
		</div>
	{:else}
		<!-- Summary Stats -->
		<div class="flex justify-between text-xs text-gray-300 mb-2 px-1">
			<span class="text-profit">
				🟢 {winnersCount} Winners: {formatCurrency(totalGains, totalCurrency)}
			</span>
			<span class="text-loss">
				🔴 {losersCount} Losers: {formatCurrency(totalLosses, totalCurrency)}
			</span>
		</div>
		
		<!-- Chart Container -->
		<div class="flex-1 min-h-0">
			<canvas bind:this={chartCanvas} class="w-full h-full"></canvas>
		</div>
	{/if}
</div>
