<script lang="ts">
	/**
	 * Login page for Cointainr authentication
	 *
	 * This page provides the main login interface with proper styling consistent
	 * with the Cointainr design system, demo mode support, and redirect logic
	 * after successful authentication.
	 */

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import LoginForm from '$lib/components/LoginForm.svelte';
	import { authActions, isAuthenticated } from '$lib/stores/authStore';
	import { devLog } from '$lib/utils/logger';
	import type { PageData } from './$types';

	export let data: PageData;

	// Extract data from page load
	$: ({ demoMode, redirectTo } = data);

	// Check if user is already authenticated and redirect if so
	$: if ($isAuthenticated) {
		handleSuccessfulLogin();
	}

	/**
	 * Handle successful login with redirect logic
	 */
	function handleSuccessfulLogin() {
		devLog.info('Login successful, redirecting to:', redirectTo);

		// Redirect to the intended page or home
		goto(redirectTo, { replaceState: true });
	}

	/**
	 * Handle login form success event
	 */
	function handleLoginSuccess(event: CustomEvent<{ username: string; demoMode: boolean }>) {
		const { username, demoMode: loginDemoMode } = event.detail;

		devLog.info('Login form success:', { username, demoMode: loginDemoMode });

		// The redirect will be handled by the reactive statement above
		// since the auth store will update isAuthenticated to true
	}

	/**
	 * Initialize authentication state on page load
	 */
	onMount(async () => {
		// Initialize auth state to check if user is already logged in
		await authActions.initializeAuth();
	});
</script>

<svelte:head>
	<title>Sign In - Cointainr</title>
	<meta name="description" content="Sign in to access your Cointainr portfolio dashboard" />
</svelte:head>

<div class="login-page">
	<div class="login-container">
		<!-- Header Section -->
		<div class="login-header">
			<div class="logo-section">
				<h1 class="app-title">Cointainr</h1>
				<p class="app-subtitle">Portfolio Management System</p>
			</div>

			{#if demoMode}
				<div class="demo-mode-notice">
					<div class="demo-icon" aria-hidden="true">
						<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
					</div>
					<div class="demo-content">
						<h3 class="demo-title">Demo Mode Active</h3>
						<p class="demo-description">
							This is a demonstration environment. Data will be reset daily at midnight.
						</p>
						<div class="demo-credentials">
							<strong>Demo Credentials:</strong>
							<button
								type="button"
								class="credential-button"
								on:click={() => navigator.clipboard?.writeText('demo')}
								title="Click to copy username"
							>
								<code class="credential-display">demo</code>
							</button>
							/
							<button
								type="button"
								class="credential-button"
								on:click={() => navigator.clipboard?.writeText('demo1')}
								title="Click to copy password"
							>
								<code class="credential-display">demo1</code>
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Login Form Section -->
		<div class="login-form-section">
			<LoginForm
				{demoMode}
				demoCredentials={{ username: 'demo', password: 'demo1' }}
				on:success={handleLoginSuccess}
			/>
		</div>

		<!-- Footer section removed -->
	</div>
</div>

<style>
	.login-page {
		min-height: 100vh;
		background-color: var(--color-background);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background-image:
			radial-gradient(circle at 20% 80%, rgba(0, 200, 150, 0.1) 0%, transparent 50%),
			radial-gradient(circle at 80% 20%, rgba(212, 175, 55, 0.1) 0%, transparent 50%);
	}

	.login-container {
		width: 100%;
		max-width: 480px;
		background-color: var(--color-surface);
		border-radius: 1rem;
		box-shadow:
			0 20px 25px -5px rgba(0, 0, 0, 0.3),
			0 10px 10px -5px rgba(0, 0, 0, 0.2);
		overflow: hidden;
	}

	.login-header {
		padding: 2rem 2rem 1rem 2rem;
		text-align: center;
		border-bottom: 1px solid rgba(240, 244, 248, 0.1);
	}

	.logo-section {
		margin-bottom: 1.5rem;
	}

	.app-title {
		font-family: var(--font-headline);
		font-size: 2.5rem;
		font-weight: 700;
		color: var(--color-gold);
		margin: 0 0 0.5rem 0;
		text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
	}

	.app-subtitle {
		font-size: 1rem;
		color: rgba(240, 244, 248, 0.7);
		margin: 0;
		font-weight: 400;
	}

	.demo-mode-notice {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(212, 175, 55, 0.05) 100%);
		border: 1px solid rgba(212, 175, 55, 0.3);
		border-radius: 0.75rem;
		padding: 1rem;
		text-align: left;
	}

	.demo-icon {
		color: var(--color-gold);
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.demo-content {
		flex: 1;
	}

	.demo-title {
		font-weight: 600;
		color: var(--color-gold);
		margin: 0 0 0.5rem 0;
		font-size: 1rem;
	}

	.demo-description {
		font-size: 0.875rem;
		color: rgba(240, 244, 248, 0.8);
		margin: 0 0 0.75rem 0;
		line-height: 1.4;
	}

	.demo-credentials {
		font-size: 0.875rem;
		color: rgba(240, 244, 248, 0.9);
		margin: 0;
	}

	.credential-button {
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.credential-button:hover {
		opacity: 0.8;
	}

	.credential-display {
		background-color: rgba(212, 175, 55, 0.2);
		color: var(--color-gold);
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.8125rem;
		font-weight: 600;
		border: 1px solid rgba(212, 175, 55, 0.3);
		pointer-events: none;
	}

	.login-form-section {
		padding: 2rem;
	}

	/* Footer styles removed */

	/* Responsive adjustments */
	@media (max-width: 640px) {
		.login-page {
			padding: 0.5rem;
			align-items: flex-start;
			padding-top: 2rem;
		}

		.login-container {
			max-width: 100%;
			border-radius: 0.75rem;
		}

		.login-header {
			padding: 1.5rem 1.5rem 1rem 1.5rem;
		}

		.app-title {
			font-size: 2rem;
		}

		.app-subtitle {
			font-size: 0.875rem;
		}

		.login-form-section {
			padding: 1.5rem;
		}

		/* Footer responsive styles removed */

		.demo-mode-notice {
			flex-direction: column;
			text-align: center;
			gap: 0.75rem;
		}

		.demo-content {
			text-align: center;
		}
	}

	/* Focus and accessibility improvements */
	@media (prefers-reduced-motion: reduce) {
		.login-page {
			background-image: none;
		}
	}

	/* High contrast mode support */
	@media (prefers-contrast: high) {
		.login-container {
			border: 2px solid var(--color-text-light);
		}

		.demo-mode-notice {
			border-width: 2px;
		}
	}
</style>
