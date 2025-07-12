<script lang="ts">
	import { getAssets } from '$lib/services/api';
	import type { Asset } from '$lib/types';
	import AddAssetForm from '$lib/components/AddAssetForm.svelte'; // Import the form

	let assetsPromise: Promise<Asset[]> = getAssets();

	// This function will be called by the form to refresh the asset list
	function handleAssetCreated() {
		assetsPromise = getAssets();
	}
</script>

<div class="bg-background text-text-light min-h-screen p-8">
	<header class="mb-8">
		<h1 class="font-headline text-4xl text-primary">Cointainr Dashboard</h1>
		<p class="font-sans mt-2 text-lg">Your consolidated asset overview.</p>
	</header>

	<AddAssetForm on:assetCreated={handleAssetCreated} />

	<main class="bg-surface rounded-lg p-6 shadow-lg">
		<h2 class="font-headline text-2xl mb-4">Your Assets</h2>

		{#await assetsPromise}
			<p>Loading assets...</p>
		{:then assets}
			{#if assets.length > 0}
				<div class="grid grid-cols-4 gap-4 font-mono">
					<div class="font-bold">Name</div>
					<div class="font-bold text-right">Quantity</div>
					<div class="font-bold text-right">Type</div>
					<div class="font-bold text-right">Symbol</div>

					{#each assets as asset (asset.id)}
						<div>{asset.name}</div>
						<div class="text-right">{asset.quantity}</div>
						<div class="text-right">{asset.type}</div>
						<div class="text-right">{asset.symbol ?? '-'}</div>
					{/each}
				</div>
			{:else}
				<p class="text-center py-4">No assets found. Add your first one to get started!</p>
			{/if}
		{:catch error}
			<p class="text-loss">Error loading assets: {error.message}</p>
		{/await}
	</main>
</div>