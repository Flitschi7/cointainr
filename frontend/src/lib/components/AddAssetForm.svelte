<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Asset } from '$lib/types';
	import { createAsset, updateAsset, deleteAsset } from '$lib/services/api';
	import Modal from '$lib/components/Modal.svelte';
	import ConfirmDeleteModal from '$lib/components/ConfirmDeleteModal.svelte';

	export let asset: Asset | null = null;

	const dispatch = createEventDispatcher();

	let formData: Partial<Omit<Asset, 'id'>> = {};
	let showConfirmDeleteModal = false;

	onMount(() => {
		if (asset) {
			formData = { ...asset };
		} else {
			formData = {
				type: 'cash',
				name: '',
				quantity: 0,
				symbol: null,
				currency: 'EUR',
				purchase_price: null
			};
		}
	});

	let isLoading = false;
	let error: string | null = null;

	async function handleSubmit() {
		// ... (This function remains unchanged)
	}

	// This function now just opens the confirmation modal
	function handleDeleteClick() {
		showConfirmDeleteModal = true;
	}

	// This function performs the actual deletion
	async function executeDelete() {
		if (!asset) return;

		showConfirmDeleteModal = false; // Close the confirmation modal
		isLoading = true;
		error = null;
		try {
			await deleteAsset(asset.id);
			dispatch('saved'); // Trigger a refresh on the main page
			dispatch('close'); // Close the main edit modal
		} catch (e: any) {
			error = e.message;
		} finally {
			isLoading = false;
		}
	}
</script>

{#if showConfirmDeleteModal}
	<Modal on:close={() => (showConfirmDeleteModal = false)}>
		<ConfirmDeleteModal on:confirm={executeDelete} on:cancel={() => (showConfirmDeleteModal = false)} />
	</Modal>
{/if}

<form on:submit|preventDefault={handleSubmit} class="space-y-4">
	<h2 class="font-headline text-2xl text-text-light mb-4">
		{asset ? 'Edit Asset' : 'Add New Asset'}
	</h2>

	<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
		<div class="md:col-span-2">
			<label for="type" class="block mb-1 font-bold text-text-light">Type</label>
			<select id="type" bind:value={formData.type} class="w-full bg-background text-text-light rounded p-2">
				<option value="cash">Cash</option>
				<option value="stock">Stock</option>
				<option value="crypto">Crypto</option>
			</select>
		</div>
		<div>
			<label for="name" class="block mb-1 font-bold text-text-light">Location/Account</label>
			<input type="text" id="name" bind:value={formData.name} required class="w-full bg-background text-text-light rounded p-2" placeholder="e.g., Trade Republic, ING" />
		</div>
		{#if formData.type !== 'cash'}
			<div>
				<label for="symbol" class="block mb-1 font-bold text-text-light">Symbol</label>
				<input type="text" id="symbol" bind:value={formData.symbol} required class="w-full bg-background text-text-light rounded p-2" placeholder="e.g., AAPL, BTC" />
			</div>
		{/if}
		<div>
			<label for="quantity" class="block mb-1 font-bold text-text-light">{formData.type === 'cash' ? 'Amount' : 'Quantity'}</label>
			<input type="number" step="any" id="quantity" bind:value={formData.quantity} required class="w-full bg-background text-text-light rounded p-2" />
		</div>
		<div>
			<label for="currency" class="block mb-1 font-bold text-text-light">Currency</label>
			<input type="text" id="currency" bind:value={formData.currency} required class="w-full bg-background text-text-light rounded p-2" placeholder="e.g., USD, EUR" />
		</div>
		{#if formData.type !== 'cash'}
			<div class="md:col-span-2">
				<label for="purchase_price" class="block mb-1 font-bold text-text-light">Purchase Price (per unit)</label>
				<input type="number" step="any" id="purchase_price" bind:value={formData.purchase_price} required class="w-full bg-background text-text-light rounded p-2" />
			</div>
		{/if}
	</div>


	<div class="flex gap-4 mt-4">
		{#if asset}
			<button type="button" on:click={handleDeleteClick} disabled={isLoading} class="bg-loss hover:opacity-80 text-white font-bold py-2 px-4 rounded w-1/3">
				{isLoading ? '...' : 'Delete'}
			</button>
		{/if}
		<button type="submit" disabled={isLoading} class="bg-primary hover:opacity-80 text-white font-bold py-2 px-4 rounded w-full">
			{#if isLoading}
				Saving...
			{:else}
				{asset ? 'Save Changes' : 'Add Asset'}
			{/if}
		</button>
	</div>

	{#if error}
		<p class="text-loss mt-4">{error}</p>
	{/if}
</form>