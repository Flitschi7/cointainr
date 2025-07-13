<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	// This function now checks what was clicked.
	// It only closes the modal if the dark backdrop itself is the click target.
	function handleClick(event: MouseEvent) {
		if (event.currentTarget === event.target) {
			dispatch('close');
		}
	}

	// This function allows closing the modal with the Escape key
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />


<div
	class="fixed inset-0 bg-background bg-opacity-90 z-50 flex justify-center items-center"
	on:click={handleClick}
	on:keydown={(event) => {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}}
	role="dialog"
	aria-modal="true"
	tabindex="0"
>
	<div class="bg-surface rounded-lg shadow-xl p-8 w-full max-w-2xl outline-none" style="font-family: var(--font-headline); color: var(--color-text-light);">
		<slot />
	</div>
</div>