<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Asset } from '$lib/types';
	import { createAsset } from '$lib/services/api';

	const dispatch = createEventDispatcher();

	let newAsset: Omit<Asset, 'id'> = {
		type: 'cash',
		name: '',
		quantity: 0,
		symbol: null,
		currency: 'EUR',
		purchase_price: null
	};

	let isLoading = false;
	let error: string | null = null;

	async function handleSubmit() {
		isLoading = true;
		error = null;
		try {
			// Filter out empty strings and convert to null
			const dataToSend = {
				...newAsset,
				symbol: newAsset.symbol || null,
				currency: newAsset.currency || null,
				purchase_price: newAsset.purchase_price ? Number(newAsset.purchase_price) : null
			};
			await createAsset(dataToSend);
			dispatch('assetCreated'); // Notify the parent component
		} catch (e: any) {
			error = e.message;
		} finally {
			isLoading = false;
		}
	}
</script>

<form on:submit|preventDefault={handleSubmit} class="bg-surface rounded-lg p-6 shadow-lg mb-8">
	<h2 class="font-headline text-2xl mb-4">Add New Asset</h2>

	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<div>
			<label for="type" class="block mb-1 font-bold">Type</label>
			<select id="type" bind:value={newAsset.type} class="w-full bg-background rounded p-2">
				<option value="cash">Cash</option>
				<option value="stock">Stock</option>
				<option value="crypto">Crypto</option>
			</select>
		</div>

		<div>
			<label for="name" class="block mb-1 font-bold">Name</label>
			<input type="text" id="name" bind:value={newAsset.name} required class="w-full bg-background rounded p-2" placeholder="e.g., Checking Account" />
		</div>

		<div>
			<label for="quantity" class="block mb-1 font-bold">Quantity</label>
			<input type="number" step="any" id="quantity" bind:value={newAsset.quantity} required class="w-full bg-background rounded p-2" />
		</div>

		<div>
			<label for="symbol" class="block mb-1 font-bold">Symbol</label>
			<input type="text" id="symbol" bind:value={newAsset.symbol} class="w-full bg-background rounded p-2" placeholder="e.g., AAPL, BTC" />
		</div>

		<div>
			<label for="currency" class="block mb-1 font-bold">Currency</label>
			<input type="text" id="currency" bind:value={newAsset.currency} class="w-full bg-background rounded p-2" placeholder="e.g., USD, EUR" />
		</div>

		<div>
			<label for="purchase_price" class="block mb-1 font-bold">Purchase Price</label>
			<input type="number" step="any" id="purchase_price" bind:value={newAsset.purchase_price} class="w-full bg-background rounded p-2" />
		</div>
	</div>

	<button type="submit" disabled={isLoading} class="bg-primary hover:opacity-80 text-white font-bold py-2 px-4 rounded mt-4 w-full">
		{#if isLoading}
			Adding...
		{:else}
			Add Asset
		{/if}
	</button>

	{#if error}
		<p class="text-loss mt-4">{error}</p>
	{/if}
</form>