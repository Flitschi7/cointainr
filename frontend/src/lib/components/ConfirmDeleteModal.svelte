<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
</script>

<div class="text-center">
	<h3 class="font-headline text-text-light mb-4 text-2xl">Confirm Deletion</h3>
	<p class="text-text-light mb-6 opacity-70">
		Are you sure you want to delete this asset? This action cannot be undone.
	</p>
	<div class="flex justify-center gap-4">
		<button
			on:click={() => dispatch('cancel')}
			class="bg-surface text-text-light rounded px-6 py-2 font-bold hover:opacity-80"
		>
			Cancel
		</button>
		<button
			on:click={() => dispatch('confirm')}
			class="bg-loss rounded px-6 py-2 font-bold text-white hover:opacity-80"
		>
			Confirm Delete
		</button>
	</div>
</div>
