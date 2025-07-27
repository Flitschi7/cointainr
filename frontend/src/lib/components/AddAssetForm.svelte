<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Asset } from '$lib/types';
	import { createAsset, updateAsset, deleteAsset } from '$lib/services/api';
	import Modal from '$lib/components/Modal.svelte';
	import ConfirmDeleteModal from '$lib/components/ConfirmDeleteModal.svelte';

	export let asset: Asset | null = null;
	const dispatch = createEventDispatcher();

	let formData: Partial<Omit<Asset, 'id'>> & { assetname?: string | null } = {};
	let showConfirmDeleteModal = false;

	onMount(() => {
		formData = asset
			? { ...asset }
			: {
					type: 'cash',
					name: '',
					assetname: '',
					quantity: 0,
					symbol: null,
					currency: 'EUR',
					purchase_price: null,
					buy_currency: 'EUR'
				};
	});

	let isLoading = false;
	let error: string | null = null;

	async function handleSubmit() {
		isLoading = true;
		error = null;
		try {
			if (asset) {
				// Edit mode
				await updateAsset(asset.id, formData);
			} else {
				// Add mode
				await createAsset(formData as Omit<Asset, 'id'>);
			}
			dispatch('saved');
			dispatch('close');
		} catch (e: unknown) {
			const errorMessage = e instanceof Error ? e.message : 'An error occurred.';
			error = errorMessage;
		} finally {
			isLoading = false;
		}
	}

	function handleDeleteClick() {
		showConfirmDeleteModal = true;
	}

	async function executeDelete() {
		if (!asset) return;
		showConfirmDeleteModal = false;
		isLoading = true;
		error = null;
		try {
			await deleteAsset(asset.id);
			dispatch('saved');
			dispatch('close');
		} catch (e: unknown) {
			const errorMessage = e instanceof Error ? e.message : 'An error occurred.';
			error = errorMessage;
		} finally {
			isLoading = false;
		}
	}
</script>

{#if showConfirmDeleteModal}
	<Modal on:close={() => (showConfirmDeleteModal = false)}>
		<ConfirmDeleteModal
			on:confirm={executeDelete}
			on:cancel={() => (showConfirmDeleteModal = false)}
		/>
	</Modal>
{/if}

<form on:submit|preventDefault={handleSubmit} class="space-y-4">
	<h2 class="font-headline text-text-light mb-4 text-2xl">
		{asset ? 'Edit Asset' : 'Add New Asset'}
	</h2>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<div class="md:col-span-2">
			<label for="type" class="text-text-light mb-1 block font-bold">Type</label>
			<select
				id="type"
				bind:value={formData.type}
				class="bg-background text-text-light w-full rounded p-2"
			>
				<option value="cash">Cash</option>
				<option value="stock">Stock</option>
				<option value="crypto">Crypto</option>
				<option value="derivative">Derivative</option>
			</select>
		</div>
		<div>
			<label for="name" class="text-text-light mb-1 block font-bold">Location/Broker</label>
			<input
				type="text"
				id="name"
				bind:value={formData.name}
				required
				class="bg-background text-text-light w-full rounded p-2"
				placeholder="e.g., Trade Republic, ING"
			/>
		</div>
		{#if formData.type !== 'cash'}
			<div>
				<label for="symbol" class="text-text-light mb-1 block font-bold">Symbol/ISIN</label>
				<input
					type="text"
					id="symbol"
					bind:value={formData.symbol}
					required
					class="bg-background text-text-light w-full rounded p-2"
					placeholder={formData.type === 'derivative' ? 'e.g., DE000HT3NZR7' : 'e.g., AAPL, BTC'}
				/>
			</div>
		{/if}
		<div>
			<label for="quantity" class="text-text-light mb-1 block font-bold"
				>{formData.type === 'cash' ? 'Amount' : 'Quantity'}</label
			>
			<input
				type="number"
				step="any"
				id="quantity"
				bind:value={formData.quantity}
				required
				class="bg-background text-text-light w-full rounded p-2"
			/>
		</div>
		<div>
			<label for="currency" class="text-text-light mb-1 block font-bold"
				>Current Price Currency</label
			>
			<input
				type="text"
				id="currency"
				bind:value={formData.currency}
				required
				class="bg-background text-text-light w-full rounded p-2"
				placeholder="e.g., USD, EUR"
			/>
		</div>
		{#if formData.type !== 'cash'}
			<div>
				<label for="buy_currency" class="text-text-light mb-1 block font-bold"
					>Buy Price Currency</label
				>
				<input
					type="text"
					id="buy_currency"
					bind:value={formData.buy_currency}
					required
					class="bg-background text-text-light w-full rounded p-2"
					placeholder="e.g., USD, EUR"
				/>
			</div>
		{/if}
		{#if formData.type !== 'cash'}
			<div class="md:col-span-2">
				<label for="purchase_price" class="text-text-light mb-1 block font-bold"
					>Purchase Price (per unit)</label
				>
				<input
					type="number"
					step="any"
					id="purchase_price"
					bind:value={formData.purchase_price}
					required
					class="bg-background text-text-light w-full rounded p-2"
				/>
			</div>
		{/if}
	</div>

	<div class="mt-4 flex gap-4">
		{#if asset}
			<button
				type="button"
				on:click={handleDeleteClick}
				disabled={isLoading}
				class="bg-loss w-1/3 rounded px-4 py-2 font-bold text-white hover:opacity-80"
			>
				{isLoading ? '...' : 'Delete'}
			</button>
		{/if}
		<button
			type="submit"
			disabled={isLoading}
			class="{asset
				? 'bg-primary'
				: 'bg-gold'} w-full rounded px-4 py-2 font-bold text-white hover:opacity-80"
		>
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
