<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
</script>

<div class="text-center">
	<h3 class="font-headline text-2xl text-text-light mb-4">Confirm Deletion</h3>
	<p class="text-gray-400 mb-6">
		Are you sure you want to delete this asset? This action cannot be undone.
	</p>
	<div class="flex justify-center gap-4">
		<button
			on:click={() => dispatch('cancel')}
			class="bg-gray-600 hover:opacity-80 text-white font-bold py-2 px-6 rounded"
		>
			Cancel
		</button>
		<button
			on:click={() => dispatch('confirm')}
			class="bg-loss hover:opacity-80 text-white font-bold py-2 px-6 rounded"
		>
			Confirm Delete
		</button>
	</div>
</div>