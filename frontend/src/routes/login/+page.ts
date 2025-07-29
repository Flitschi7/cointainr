/**
 * Login page load function
 *
 * This function handles server-side logic for the login page,
 * including demo mode detection and authentication status checks.
 */

import type { PageLoad } from './$types';
import { authApiService } from '$lib/services/authApi';
import { redirect } from '@sveltejs/kit';

export const load: PageLoad = async ({ url, fetch }) => {
	try {
		// Check if user is already authenticated
		const authStatus = await authApiService.checkAuthStatus();

		if (authStatus.authenticated) {
			// User is already logged in, redirect to intended page or home
			const redirectTo = url.searchParams.get('redirect') || '/';
			throw redirect(302, redirectTo);
		}

		// Return page data including demo mode status
		return {
			demoMode: authStatus.demo_mode || false,
			redirectTo: url.searchParams.get('redirect') || '/'
		};
	} catch (error) {
		// If it's a redirect, re-throw it
		if (error && typeof error === 'object' && 'status' in error) {
			throw error;
		}

		// For other errors, continue to login page
		console.warn('Auth status check failed during page load:', error);

		return {
			demoMode: false,
			redirectTo: url.searchParams.get('redirect') || '/'
		};
	}
};
