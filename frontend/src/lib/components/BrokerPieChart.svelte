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

	// Generate a color palette for brokers
	function generateBrokerColors(count: number): string[] {
		const colors = [
			'#10B981', // Emerald
			'#F59E0B', // Amber
			'#8B5CF6', // Purple
			'#EF4444', // Red
			'#3B82F6', // Blue
			'#F97316', // Orange
			'#06B6D4', // Cyan
			'#84CC16', // Lime
			'#EC4899', // Pink
			'#6B7280', // Gray
			'#14B8A6', // Teal
			'#F472B6', // Pink-400
			'#A855F7', // Purple-500
			'#22D3EE', // Cyan-400
			'#FDE047', // Yellow-300
		];

		// If we need more colors than we have, generate additional ones
		if (count > colors.length) {
			for (let i = colors.length; i < count; i++) {
				// Generate a random HSL color with good saturation and lightness
				const hue = (i * 137.508) % 360; // Golden angle for better distribution
				colors.push(`hsl(${hue}, 65%, 55%)`);
			}
		}

		return colors.slice(0, count);
	}

	// Calculate asset distribution by broker/location
	function calculateBrokerDistribution() {
		const distribution: { [broker: string]: number } = {};

		assets.forEach(asset => {
			let value = 0;
			const brokerName = asset.name || 'Unknown Broker';

			if (asset.type === 'cash') {
				value = asset.quantity;
			} else {
				const priceData = assetPrices.get(asset.id);
				if (priceData) {
					value = priceData.price * asset.quantity;
				}
			}

			if (distribution[brokerName]) {
				distribution[brokerName] += value;
			} else {
				distribution[brokerName] = value;
			}
		});

		return distribution;
	}

	function createChart() {
		if (!chartCanvas) return;

		const distribution = calculateBrokerDistribution();
		const brokers = Object.keys(distribution);
		const total = Object.values(distribution).reduce((sum, value) => sum + value, 0);

		// Only show chart if there's data
		if (total === 0 || brokers.length === 0) return;

		// Sort brokers by value (largest first)
		const sortedBrokers = brokers.sort((a, b) => distribution[b] - distribution[a]);
		
		const data = sortedBrokers.map(broker => distribution[broker]);
		const labels = sortedBrokers;
		const colors = generateBrokerColors(sortedBrokers.length);

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
										
										// Truncate long broker names for legend
										const displayLabel = String(label).length > 15 ? 
											String(label).substring(0, 15) + '...' : 
											String(label);
										
										return {
											text: `${displayLabel}: ${formatCurrency(value, totalCurrency)} (${percentage}%)`,
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
								return String(context[0].label);
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
			<div class="text-4xl mb-2">🏦</div>
			<p>No assets to display</p>
		</div>
	{:else}
		<canvas bind:this={chartCanvas} class="max-w-full max-h-full"></canvas>
	{/if}
</div>
