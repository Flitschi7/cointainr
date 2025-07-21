/**
 * Application initialization utilities
 *
 * This module provides functions for initializing various aspects of the application,
 * such as error handlers, analytics, and other global services.
 */

import { browser } from '$app/environment';
import { initializeGlobalErrorHandlers } from './errorHandler';

/**
 * Initialize the application
 * This function should be called once when the application starts
 */
export function initializeApp(): void {
	if (browser) {
		// Initialize global error handlers
		initializeGlobalErrorHandlers();

		// Log initialization
		console.info('Application initialized');
	}
}
