<script lang="ts">
	/**
	 * LoginForm component for user authentication
	 *
	 * This component provides a login form with validation, demo mode support,
	 * error handling, and loading states for the authentication system.
	 */

	import { createEventDispatcher } from 'svelte';
	import { authActions, isLoading, authError } from '$lib/stores/authStore';
	import LoadingIndicator from './LoadingIndicator.svelte';
	import ErrorState from './ErrorState.svelte';

	const dispatch = createEventDispatcher<{
		success: { username: string; demoMode: boolean };
	}>();

	// Props
	export let demoMode: boolean = false;
	export let demoCredentials: { username: string; password: string } = {
		username: 'demo',
		password: 'demo1'
	};

	// Form state
	let username = '';
	let password = '';
	let formErrors: { username?: string; password?: string } = {};
	let showPassword = false;

	// Reactive statements
	$: isFormValid = username.trim() !== '' && password.trim() !== '';
	$: canSubmit = isFormValid && !$isLoading;

	// Auto-fill demo credentials when in demo mode
	$: if (demoMode && username === '' && password === '') {
		username = demoCredentials.username;
		password = demoCredentials.password;
	}

	/**
	 * Validate form fields
	 */
	function validateForm(): boolean {
		formErrors = {};

		if (!username.trim()) {
			formErrors.username = 'Username is required';
		}

		if (!password.trim()) {
			formErrors.password = 'Password is required';
		}

		return Object.keys(formErrors).length === 0;
	}

	/**
	 * Handle form submission
	 */
	async function handleSubmit(event: Event) {
		event.preventDefault();

		// Clear any previous auth errors
		authActions.clearError();

		// Validate form
		if (!validateForm()) {
			return;
		}

		try {
			const success = await authActions.login(username.trim(), password.trim());

			if (success) {
				// Dispatch success event with user info
				dispatch('success', {
					username: username.trim(),
					demoMode
				});

				// Reset form
				if (!demoMode) {
					username = '';
					password = '';
				}
				formErrors = {};
			}
		} catch (error) {
			// Error is handled by the auth store
			console.error('Login submission error:', error);
		}
	}

	/**
	 * Handle retry after error
	 */
	function handleRetry() {
		authActions.clearError();
		// Focus on username field for retry
		const usernameInput = document.getElementById('username') as HTMLInputElement;
		if (usernameInput) {
			usernameInput.focus();
		}
	}

	/**
	 * Toggle password visibility
	 */
	function togglePasswordVisibility() {
		showPassword = !showPassword;
	}

	/**
	 * Handle input changes to clear field-specific errors
	 */
	function handleUsernameChange() {
		if (formErrors.username) {
			formErrors.username = undefined;
		}
	}

	function handlePasswordChange() {
		if (formErrors.password) {
			formErrors.password = undefined;
		}
	}
</script>

<div class="login-form-container">
	<!-- Removed login form header -->

	<form on:submit={handleSubmit} class="login-form" novalidate>
		<!-- Username Field -->
		<div class="form-group">
			<label for="username" class="form-label">Username</label>
			<input
				id="username"
				type="text"
				bind:value={username}
				on:input={handleUsernameChange}
				class="form-input {formErrors.username ? 'error' : ''}"
				placeholder="Enter your username"
				disabled={$isLoading}
				autocomplete="username"
				required
			/>
			{#if formErrors.username}
				<p class="field-error" role="alert">{formErrors.username}</p>
			{/if}
		</div>

		<!-- Password Field -->
		<div class="form-group">
			<label for="password" class="form-label">Password</label>
			<div class="password-input-container">
				<input
					id="password"
					type={showPassword ? 'text' : 'password'}
					bind:value={password}
					on:input={handlePasswordChange}
					class="form-input password-input {formErrors.password ? 'error' : ''}"
					placeholder="Enter your password"
					disabled={$isLoading}
					autocomplete="current-password"
					required
				/>
				<button
					type="button"
					class="password-toggle"
					on:click={togglePasswordVisibility}
					disabled={$isLoading}
					aria-label={showPassword ? 'Hide password' : 'Show password'}
				>
					{#if showPassword}
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"
							></path>
						</svg>
					{:else}
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
							></path>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
							></path>
						</svg>
					{/if}
				</button>
			</div>
			{#if formErrors.password}
				<p class="field-error" role="alert">{formErrors.password}</p>
			{/if}
		</div>

		<!-- Auth Error Display -->
		{#if $authError}
			<div class="auth-error">
				<ErrorState message={$authError} severity="error" onRetry={handleRetry} showIcon={true} />
			</div>
		{/if}

		<!-- Submit Button -->
		<button type="submit" class="submit-button" disabled={!canSubmit}>
			{#if $isLoading}
				<LoadingIndicator size="small" inline={true} color="light" />
				<span>Signing In...</span>
			{:else}
				<span>Sign In</span>
			{/if}
		</button>
	</form>
</div>

<style>
	.login-form-container {
		width: 100%;
		max-width: 400px;
		margin: 0 auto;
	}

	/* Removed unused header and demo banner styles */

	.login-form {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.form-label {
		font-weight: 500;
		color: var(--color-text-light);
		font-size: 0.875rem;
	}

	.form-input {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid rgba(240, 244, 248, 0.2);
		border-radius: 0.375rem;
		background-color: var(--color-surface);
		color: var(--color-text-light);
		font-size: 1rem;
		box-sizing: border-box;
		transition:
			border-color 0.2s,
			box-shadow 0.2s;
	}

	.form-input:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px rgba(0, 200, 150, 0.1);
	}

	.form-input.error {
		border-color: var(--color-loss);
		box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
	}

	.form-input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.form-input::placeholder {
		color: rgba(240, 244, 248, 0.5);
	}

	.password-input-container {
		position: relative;
		width: 100%;
	}

	.password-input {
		width: 100%;
		padding-right: 3rem;
		box-sizing: border-box;
	}

	.password-toggle {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		background: none;
		border: none;
		color: rgba(240, 244, 248, 0.6);
		cursor: pointer;
		padding: 0.25rem;
		border-radius: 0.25rem;
		transition: color 0.2s;
	}

	.password-toggle:hover:not(:disabled) {
		color: var(--color-text-light);
	}

	.password-toggle:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.field-error {
		color: var(--color-loss);
		font-size: 0.75rem;
		margin: 0;
	}

	.auth-error {
		margin: -0.5rem 0 0.5rem 0;
	}

	.submit-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.875rem 1.5rem;
		background-color: var(--color-primary);
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-weight: 600;
		font-size: 1rem;
		cursor: pointer;
		transition:
			background-color 0.2s,
			opacity 0.2s;
		min-height: 3rem;
	}

	.submit-button:hover:not(:disabled) {
		background-color: #00b085;
	}

	.submit-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.submit-button:focus {
		outline: none;
		box-shadow: 0 0 0 3px rgba(0, 200, 150, 0.3);
	}

	/* Responsive adjustments */
	@media (max-width: 480px) {
		.login-form-container {
			max-width: 100%;
			padding: 0 1rem;
		}
	}
</style>
