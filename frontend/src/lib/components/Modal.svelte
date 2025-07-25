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
	class="bg-background bg-opacity-90 fixed inset-0 z-50 flex items-center justify-center p-4"
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
	<div
		class="bg-surface w-full max-w-2xl rounded-lg p-4 sm:p-6 lg:p-8 shadow-xl outline-none max-h-[90vh] overflow-y-auto"
		style="font-family: var(--font-headline); color: var(--color-text-light);"
	>
		<slot />
	</div>
</div>
