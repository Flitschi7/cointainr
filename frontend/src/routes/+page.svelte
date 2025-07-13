<script lang="ts">
	import { getAssets } from '$lib/services/api';
	import type { Asset } from '$lib/types';
	import AddAssetForm from '$lib/components/AddAssetForm.svelte';
	import Modal from '$lib/components/Modal.svelte';

	let assetsPromise: Promise<Asset[]> = getAssets();
	let showModal = false;
	let assetToEdit: Asset | null = null;

	let allAssets: Asset[] = [];
	$: assetsPromise.then((data) => (allAssets = data || []));

	let filterLocation = '';
	let filterSymbol = '';
	let filterType: 'all' | 'cash' | 'stock' | 'crypto' = 'all';

	$: filteredAssets = allAssets.filter((asset) => {
		const locationMatch = !filterLocation || asset.name.toLowerCase().includes(filterLocation.toLowerCase());
		const symbolMatch = !filterSymbol || (asset.symbol && asset.symbol.toLowerCase().includes(filterSymbol.toLowerCase()));
		const typeMatch = filterType === 'all' || asset.type === filterType;
		return locationMatch && symbolMatch && typeMatch;
	});

	function openAddModal() {
		assetToEdit = null;
		showModal = true;
	}

	function openEditModal(asset: Asset) {
		assetToEdit = asset;
		showModal = true;
	}

	function handleSave() {
		// Just refresh the whole list after any save/delete
		assetsPromise = getAssets();
	}
</script>

{#if showModal}
	<Modal on:close={() => (showModal = false)}>
		<AddAssetForm asset={assetToEdit} on:saved={handleSave} on:close={() => (showModal = false)} />
	</Modal>
{/if}

<div class="bg-background text-text-light min-h-screen p-8">
	<header class="mb-8">
		<h1 class="font-headline text-4xl text-primary">Cointainr Dashboard</h1>
		<p class="font-sans mt-2 text-lg">Your consolidated asset overview.</p>
	</header>

	<section class="bg-surface rounded-lg p-4 mb-8 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<input type="text" bind:value={filterLocation} placeholder="Location/Broker..." class="bg-background rounded p-2" />
			<input type="text" bind:value={filterSymbol} placeholder="Symbol..." class="bg-background rounded p-2" />
			<select bind:value={filterType} class="bg-background rounded p-2">
				<option value="all">All Types</option>
				<option value="cash">Cash</option>
				<option value="stock">Stock</option>
				<option value="crypto">Crypto</option>
			</select>
		</div>
		<button on:click={openAddModal} class="bg-primary hover:opacity-80 text-white font-bold py-2 px-4 rounded">
			Add Asset
		</button>
	</section>

	<main class="bg-surface rounded-lg p-6 shadow-lg">
		<h2 class="font-headline text-2xl mb-4">Your Assets</h2>
		{#await assetsPromise}
			<p>Loading assets...</p>
		{:then _}
			{#if filteredAssets.length > 0}
				<div class="grid grid-cols-6 gap-4 font-mono p-2 border-b border-gray-700">
					<div class="font-bold col-span-2">Location/Broker</div>
					<div class="font-bold">Symbol</div>
					<div class="font-bold">Type</div>
					<div class="font-bold text-right">Value</div>
					<div class="font-bold text-right">Quantity</div>
					<div class="font-bold text-right">Purchase Price</div>
				</div>
				<div class="font-mono">
					{#each filteredAssets as asset (asset.id)}
						<div on:click={() => openEditModal(asset)} class="grid grid-cols-6 gap-4 p-2 border-b border-gray-800 items-center cursor-pointer hover:bg-gray-800">
							<div class="col-span-2">{asset.name}</div>
							<div>{asset.symbol ?? '-'}</div>
							<div class="capitalize">{asset.type}</div>
							<div class="text-right">
								{#if asset.type === 'cash'}
									{asset.quantity.toFixed(2)} {asset.currency}
								{:else if asset.purchase_price}
									{(asset.quantity * asset.purchase_price).toFixed(2)} {asset.currency}
								{:else}
									-
								{/if}
							</div>
							<div class="text-right">
								{#if asset.type === 'cash'}
									-
								{:else}
									{asset.quantity}
								{/if}
							</div>
							<div class="text-right">
								{#if asset.purchase_price}
									{asset.purchase_price.toFixed(2)}
								{:else}
									-
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-center py-4">No matching assets found.</p>
			{/if}
		{:catch error}
			<p class="text-loss">Error loading assets: {error.message}</p>
		{/await}
	</main>
</div>