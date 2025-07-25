<script lang="ts">
	/**
	 * TransitionWrapper component for smooth transitions between loading and loaded states
	 *
	 * This component provides a standardized way to transition between loading states
	 * and loaded content with configurable animations.
	 */

	import { fade, fly, slide } from 'svelte/transition';
	import { onMount } from 'svelte';

	export let isLoading: boolean = false;
	export let loadingDelay: number = 200; // Delay before showing loading state to prevent flashing
	export let transitionDuration: number = 200;
	export let transitionType: 'fade' | 'fly' | 'slide' = 'fade';
	export let showLoadingImmediately: boolean = false; // Whether to show loading state immediately without delay

	let showLoading = false;
	let timer: ReturnType<typeof setTimeout> | null = null;

	// Handle loading state changes with delay to prevent flashing
	$: {
		if (isLoading) {
			if (showLoadingImmediately) {
				showLoading = true;
			} else {
				// Clear any existing timer
				if (timer) clearTimeout(timer);

				// Set a timer to show loading state after delay
				timer = setTimeout(() => {
					showLoading = true;
				}, loadingDelay);
			}
		} else {
			// Clear timer if loading finished before delay
			if (timer) {
				clearTimeout(timer);
				timer = null;
			}
			showLoading = false;
		}
	}

	// Clean up timer on component destruction
	onMount(() => {
		return () => {
			if (timer) clearTimeout(timer);
		};
	});

	// Get the appropriate transition based on type
	function getTransition(node: HTMLElement) {
		const options = { duration: transitionDuration };

		switch (transitionType) {
			case 'fly':
				return fly(node, { y: 10, ...options });
			case 'slide':
				return slide(node, options);
			case 'fade':
			default:
				return fade(node, options);
		}
	}
</script>

<div class="transition-wrapper">
	{#if showLoading && isLoading}
		<div transition:fade={{ duration: transitionDuration }}>
			<slot name="loading"></slot>
		</div>
	{:else if !isLoading}
		<div in:getTransition>
			<slot></slot>
		</div>
	{/if}
</div>

<style>
	.transition-wrapper {
		position: relative;
		min-height: 1.5rem;
	}
</style>
