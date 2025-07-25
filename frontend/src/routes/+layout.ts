/**
 * Root layout for the application
 *
 * This file is executed when the application starts and is responsible for
 * initializing global services and handling layout-level concerns.
 */

import { initializeApp } from '$lib/utils/initializeApp';

// Initialize the application
initializeApp();

// Export empty load function to satisfy SvelteKit
export function load() {
	return {};
}
