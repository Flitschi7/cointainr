/**
 * Application initialization utilities
 *
 * This module provides functions for initializing various aspects of the application,
 * such as error handlers, analytics, and other global services.
 */

import { browser } from '$app/environment';
import { initializeGlobalErrorHandlers } from './errorHandler';
import { authActions } from '$lib/stores/authStore';

/**
 * Initialize the application
 * This function should be called once when the application starts
 */
export function initializeApp(): void {
	if (browser) {
		// Initialize global error handlers
		initializeGlobalErrorHandlers();

		// Initialize authentication state from stored session
		authActions.initializeAuth().catch((error) => {
			console.warn('Failed to initialize authentication:', error);
		});

		// Log initialization
		console.info('Application initialized');
	}
}
