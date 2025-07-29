<script lang="ts">
	import { authActions, currentUser } from '$lib/stores/authStore';
	import { goto } from '$app/navigation';

	let isLoggingOut = false;

	async function handleLogout() {
		if (isLoggingOut) return;

		isLoggingOut = true;
		try {
			await authActions.logout();
			// Redirect to login page after successful logout
			await goto('/login');
		} catch (error) {
			console.error('Logout failed:', error);
			// Even if logout API fails, redirect to login
			await goto('/login');
		} finally {
			isLoggingOut = false;
		}
	}
</script>

<div class="flex items-center gap-3">
	{#if $currentUser.username}
		<div class="hidden items-center gap-2 text-sm text-gray-400 sm:flex">
			<span>Welcome, {$currentUser.username}</span>
			{#if $currentUser.demoMode}
				<span class="bg-coin-gold text-background rounded px-2 py-1 text-xs font-medium">
					DEMO
				</span>
			{/if}
		</div>
	{/if}

	<button
		class="bg-surface hover:bg-background text-text-light flex items-center gap-2 rounded-lg border border-gray-600 px-3 py-2 text-sm font-medium transition-all duration-200 hover:border-gray-500 disabled:cursor-not-allowed disabled:opacity-50"
		on:click={handleLogout}
		disabled={isLoggingOut}
		title="Sign out"
	>
		<span class="text-base">🚪</span>
		<span class="hidden sm:inline">
			{isLoggingOut ? 'Signing out...' : 'Sign out'}
		</span>
	</button>
</div>
