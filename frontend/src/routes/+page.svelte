
<script lang="ts">
import ValueCell from '$lib/components/ValueCell.svelte';
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
	showModal = false;
	assetToEdit = null;
	assetsPromise = getAssets();
}
</script>


{#if showModal}
	<Modal on:close={() => { showModal = false; assetToEdit = null; }}>
		<AddAssetForm
			asset={assetToEdit}
			on:saved={handleSave}
			on:close={() => { showModal = false; assetToEdit = null; }}
		/>
	</Modal>
{/if}

<div class="bg-background text-text-light min-h-screen p-8">
	<header class="mb-8">
		<h1 class="font-headline text-4xl" style="color: var(--color-primary);">Cointainr Dashboard</h1>
		<p class="font-sans mt-2 text-lg">Your consolidated asset overview.</p>
	</header>

	<section class="bg-surface rounded-lg p-4 mb-8 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<input type="text" bind:value={filterLocation} placeholder="Location/Broker..." class="bg-background text-text-light rounded p-2" />
			<input type="text" bind:value={filterSymbol} placeholder="Symbol..." class="bg-background text-text-light rounded p-2" />
			<select bind:value={filterType} class="bg-background text-text-light rounded p-2">
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
				<div class="overflow-x-auto">
					<table class="w-full font-mono border-separate border-spacing-0">
						<thead>
							<tr class="border-b border-surface">
<th class="font-bold text-left px-4 py-2 col-span-2">Location/Broker</th>
<th class="font-bold text-left px-4 py-2">Symbol</th>
<th class="font-bold text-left px-4 py-2">Type</th>
<th class="font-bold text-right px-4 py-2">Current Price</th>
<th class="font-bold text-right px-4 py-2">Value</th>
<th class="font-bold text-right px-4 py-2">Quantity</th>
<th class="font-bold text-right px-4 py-2">Purchase Price</th>
<th class="font-bold text-right px-4 py-2">Currency</th>
							</tr>
						</thead>
						<tbody>
							{#each filteredAssets as asset (asset.id)}
								<tr
									tabindex="0"
									on:click={() => openEditModal(asset)}
									on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && openEditModal(asset)}
									class="hover:bg-surface cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary border-b border-background transition-colors"
									aria-label={`Edit asset ${asset.name}`}
								>
									<td class="px-4 py-2 col-span-2">{asset.name}</td>
									<td class="px-4 py-2">{asset.symbol ?? '-'}</td>
									<td class="px-4 py-2 capitalize">{asset.type}</td>
<td class="px-4 py-2 text-right">
	{#if asset.type === 'cash'}
		-
	{:else if asset.type === 'stock' || asset.type === 'crypto'}
		<ValueCell symbol={asset.symbol ?? ''} quantity={1} currency={asset.buy_currency ?? asset.currency ?? 'USD'} />
	{:else}
		-
	{/if}
</td>
<td class="px-4 py-2 text-right">
	{#if asset.type === 'cash'}
		{asset.quantity.toFixed(2)} {asset.currency}
	{:else if asset.type === 'stock' || asset.type === 'crypto'}
		<ValueCell symbol={asset.symbol ?? ''} quantity={asset.quantity} currency={asset.buy_currency ?? asset.currency ?? 'USD'} />
	{:else}
		-
	{/if}
</td>
									<td class="px-4 py-2 text-right">
										{#if asset.type === 'cash'}
											-
										{:else}
											{asset.quantity}
										{/if}
									</td>
									<td class="px-4 py-2 text-right">
										{#if asset.purchase_price}
											{asset.purchase_price.toFixed(2)}
										{:else}
											-
										{/if}
									</td>
<td class="px-4 py-2 text-right">
	{asset.buy_currency ?? asset.currency ?? '-'}
</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-center py-4">No matching assets found.</p>
			{/if}
		{:catch error}
			<p class="text-loss">Error loading assets: {error.message}</p>
		{/await}
	</main>
</div>