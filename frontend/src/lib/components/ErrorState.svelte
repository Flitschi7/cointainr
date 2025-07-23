<script lang="ts">
	/**
	 * ErrorState component for displaying error messages with retry functionality
	 *
	 * This component provides a standardized way to display errors in the application
	 * with optional retry functionality and different visual styles based on severity.
	 */

	export let message: string = 'An error occurred';
	export let details: string | null = null;
	export let onRetry: (() => void) | null = null;
	export let severity: 'error' | 'warning' | 'info' = 'error';
	export let inline: boolean = false;
	export let showIcon: boolean = true;

	// Get appropriate icon based on severity
	function getIcon(): string {
		switch (severity) {
			case 'error':
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>`;
			case 'warning':
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>`;
			case 'info':
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>`;
		}
	}

	// Get appropriate color classes based on severity
	function getColorClasses(): string {
		switch (severity) {
			case 'error':
				return 'bg-red-100 text-red-800 border-red-200';
			case 'warning':
				return 'bg-yellow-100 text-yellow-800 border-yellow-200';
			case 'info':
				return 'bg-blue-100 text-blue-800 border-blue-200';
		}
	}

	$: icon = getIcon();
	$: colorClasses = getColorClasses();
</script>

{#if inline}
	<span class="error-state-inline {severity}" title={details || message}>
		{#if showIcon}
			<span class="icon" aria-hidden="true">
				{@html icon}
			</span>
		{/if}
		<span class="message">{message}</span>
		{#if onRetry}
			<button
				type="button"
				class="retry-button"
				on:click|preventDefault={onRetry}
				aria-label="Retry"
			>
				<svg
					class="h-4 w-4"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					xmlns="http://www.w3.org/2000/svg"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
					></path>
				</svg>
			</button>
		{/if}
	</span>
{:else}
	<div class="error-state {colorClasses}" role="alert">
		<div class="flex items-center">
			{#if showIcon}
				<div class="icon-container" aria-hidden="true">
					{@html icon}
				</div>
			{/if}
			<div class="message-container">
				<p class="message">{message}</p>
				{#if details}
					<p class="details">{details}</p>
				{/if}
			</div>
		</div>
		{#if onRetry}
			<div class="retry-container">
				<button type="button" class="retry-button" on:click|preventDefault={onRetry}>
					<svg
						class="mr-1 h-4 w-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						></path>
					</svg>
					Retry
				</button>
			</div>
		{/if}
	</div>
{/if}

<style>
	.error-state {
		padding: 0.75rem;
		border-radius: 0.375rem;
		border: 1px solid;
		margin-bottom: 1rem;
	}

	.error-state-inline {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.875rem;
	}

	.error-state-inline.error {
		color: #ef4444;
	}

	.error-state-inline.warning {
		color: #f59e0b;
	}

	.error-state-inline.info {
		color: #3b82f6;
	}

	.icon-container {
		margin-right: 0.75rem;
		display: flex;
		align-items: center;
	}

	.message-container {
		flex: 1;
	}

	.message {
		font-weight: 500;
	}

	.details {
		font-size: 0.875rem;
		margin-top: 0.25rem;
		opacity: 0.8;
	}

	.retry-container {
		margin-top: 0.75rem;
		display: flex;
		justify-content: flex-end;
	}

	.retry-button {
		display: inline-flex;
		align-items: center;
		padding: 0.375rem 0.75rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 500;
		background-color: rgba(255, 255, 255, 0.2);
		transition: background-color 0.2s;
	}

	.retry-button:hover {
		background-color: rgba(255, 255, 255, 0.3);
	}

	.error-state-inline .retry-button {
		padding: 0.125rem;
		border-radius: 0.25rem;
	}

	.icon {
		display: inline-flex;
		align-items: center;
	}
</style>
