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

<button
	class="bg-surface hover:bg-background text-text-light flex cursor-pointer items-center gap-2 rounded-lg border border-gray-600 px-3 py-2.5 text-sm font-medium transition-all duration-200 hover:border-gray-500 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
	on:click={handleLogout}
	disabled={isLoggingOut}
	title="Sign out"
>
	<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			stroke-width="2"
			d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
		></path>
	</svg>
	<span class="hidden sm:inline">
		{isLoggingOut ? 'Signing out...' : 'Sign out'}
	</span>
</button>
