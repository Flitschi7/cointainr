/**
 * Utility functions for managing loading states
 */

import { writable, derived } from 'svelte/store';

/**
 * Creates a loading state store with helper methods
 *
 * @param initialState - Initial loading state (default: false)
 * @returns Loading state store with helper methods
 */
export function createLoadingState(initialState: boolean = false) {
	const { subscribe, set, update } = writable(initialState);

	return {
		subscribe,
		start: () => set(true),
		stop: () => set(false),
		toggle: () => update((state) => !state),

		/**
		 * Wraps an async function with loading state management
		 *
		 * @param asyncFn - Async function to wrap
		 * @returns Wrapped function that manages loading state
		 */
		withLoading: <T extends any[], R>(asyncFn: (...args: T) => Promise<R>) => {
			return async (...args: T): Promise<R> => {
				set(true);
				try {
					return await asyncFn(...args);
				} finally {
					set(false);
				}
			};
		}
	};
}

/**
 * Creates a loading state store for multiple operations
 *
 * @returns Loading state store with methods for tracking multiple operations
 */
export function createMultiLoadingState() {
	const operations = writable<Record<string, boolean>>({});
	const isLoading = derived(operations, ($ops) => Object.values($ops).some(Boolean));

	return {
		subscribe: isLoading.subscribe,
		operations: {
			subscribe: operations.subscribe
		},

		/**
		 * Start loading for a specific operation
		 *
		 * @param key - Operation identifier
		 */
		startOperation: (key: string) => {
			operations.update((ops) => ({ ...ops, [key]: true }));
		},

		/**
		 * Stop loading for a specific operation
		 *
		 * @param key - Operation identifier
		 */
		stopOperation: (key: string) => {
			operations.update((ops) => ({ ...ops, [key]: false }));
		},

		/**
		 * Wraps an async function with loading state management for a specific operation
		 *
		 * @param key - Operation identifier
		 * @param asyncFn - Async function to wrap
		 * @returns Wrapped function that manages loading state
		 */
		withOperationLoading: <T extends any[], R>(
			key: string,
			asyncFn: (...args: T) => Promise<R>
		) => {
			return async (...args: T): Promise<R> => {
				operations.update((ops) => ({ ...ops, [key]: true }));
				try {
					return await asyncFn(...args);
				} finally {
					operations.update((ops) => ({ ...ops, [key]: false }));
				}
			};
		}
	};
}

/**
 * Debounces a loading state to prevent flickering for fast operations
 *
 * @param isLoading - Loading state to debounce
 * @param delay - Delay in milliseconds before showing loading state
 * @returns Debounced loading state
 */
export function debounceLoadingState(isLoading: boolean, delay: number = 200): Promise<boolean> {
	return new Promise((resolve) => {
		if (!isLoading) {
			resolve(false);
			return;
		}

		const timer = setTimeout(() => {
			resolve(isLoading);
		}, delay);

		return () => clearTimeout(timer);
	});
}
