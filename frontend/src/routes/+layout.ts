/**
 * Root layout for the application
 *
 * This file is executed when the application starts and is responsible for
 * initializing global services and handling layout-level concerns.
 */

import type { LayoutLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { authApiService } from '$lib/services/authApi';
import { initializeApp } from '$lib/utils/initializeApp';

// Initialize the application
initializeApp();

export const load: LayoutLoad = async ({ url, fetch }) => {
	// Skip authentication check for login page
	if (url.pathname === '/login') {
		return {};
	}

	try {
		// First check if authentication is enabled
		const authConfig = await authApiService.getAuthConfig(fetch);

		if (!authConfig.auth_enabled) {
			// Authentication is disabled, proceed without any auth checks
			return {};
		}

		// Authentication is enabled, check authentication status
		const authStatus = await authApiService.checkAuthStatus(fetch);

		if (!authStatus.authenticated) {
			// User is not authenticated, redirect to login with return URL
			const redirectTo = url.pathname + url.search;
			throw redirect(302, `/login?redirect=${encodeURIComponent(redirectTo)}`);
		}

		// User is authenticated, return auth info
		return {
			user: {
				username: authStatus.username,
				demoMode: authStatus.demo_mode,
				expiresAt: authStatus.expires_at
			}
		};
	} catch (error) {
		// If it's a redirect, re-throw it
		if (error && typeof error === 'object' && 'status' in error) {
			throw error;
		}

		// For other errors, continue without authentication (auth might be disabled)
		console.warn('Auth status check failed in layout:', error);
		return {};
	}
};
