<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, type ChartConfiguration } from 'chart.js/auto';
	import type { Asset } from '$lib/types';
	import { formatCurrency } from '$lib/utils/numberFormat';

	export let assets: Asset[] = [];
	export let totalCurrency: string = 'EUR';
	export let assetPrices: Map<number, { price: number; currency: string }> = new Map();
	export let refreshTrigger: number = 0;

	let chartCanvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	// Calculate asset distribution by type
	function calculateAssetDistribution() {
		const distribution = {
			cash: 0,
			stock: 0,
			crypto: 0
		};

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

			if (asset.type in distribution) {
				distribution[asset.type as keyof typeof distribution] += value;
			}
		});

		return distribution;
	}

	function createChart() {
		if (!chartCanvas) return;

		const distribution = calculateAssetDistribution();
		const total = distribution.cash + distribution.stock + distribution.crypto;

		// Only show chart if there's data
		if (total === 0) return;

		const data = [];
		const labels = [];
		const colors = [];

		if (distribution.cash > 0) {
			data.push(distribution.cash);
			labels.push(`Cash`);
			colors.push('#9CA3AF'); // Lighter gray for better visibility
		}

		if (distribution.stock > 0) {
			data.push(distribution.stock);
			labels.push(`Stocks`);
			colors.push('#10B981'); // Emerald green for better contrast
		}

		if (distribution.crypto > 0) {
			data.push(distribution.crypto);
			labels.push(`Crypto`);
			colors.push('#F59E0B'); // Amber/orange for better visibility than gold
		}

		const config: ChartConfiguration = {
			type: 'pie',
			data: {
				labels,
				datasets: [{
					data,
					backgroundColor: colors,
					borderColor: '#2A2F45', // Surface color for borders
					borderWidth: 2
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: true,
				plugins: {
					legend: {
						position: 'bottom',
						labels: {
							color: '#F0F4F8', // Text light color - white/light gray
							padding: 20,
							font: {
								size: 14,
								weight: 'bold'
							},
							usePointStyle: true,
							generateLabels: function(chart) {
								const data = chart.data;
								if (data.labels && data.datasets.length) {
									return data.labels.map((label, i) => {
										const dataset = data.datasets[0];
										const value = dataset.data[i] as number;
										const percentage = ((value / total) * 100).toFixed(1);
										
										return {
											text: `${label}: ${formatCurrency(value, totalCurrency)} (${percentage}%)`,
											fillStyle: Array.isArray(dataset.backgroundColor) ? dataset.backgroundColor[i] : dataset.backgroundColor,
											strokeStyle: '#F0F4F8', // White stroke for better visibility
											lineWidth: 1,
											index: i,
											fontColor: '#F0F4F8' // Explicit font color
										};
									});
								}
								return [];
							}
						}
					},
					tooltip: {
						backgroundColor: '#1E1E2F', // Background color
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
								return context[0].label;
							},
							label: function(context) {
								const value = context.parsed;
								const percentage = ((value / total) * 100).toFixed(1);
								return `${formatCurrency(value, totalCurrency)} (${percentage}%)`;
							}
						}
					}
				},
				elements: {
					arc: {
						borderWidth: 2
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
</script>

<div class="w-full h-64 flex items-center justify-center">
	{#if assets.length === 0}
		<div class="text-center text-gray-400">
			<div class="text-4xl mb-2">📊</div>
			<p>No assets to display</p>
		</div>
	{:else}
		<canvas bind:this={chartCanvas} class="max-w-full max-h-full"></canvas>
	{/if}
</div>
