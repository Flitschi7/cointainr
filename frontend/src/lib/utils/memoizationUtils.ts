/**
 * Utility functions for memoization to optimize rendering performance
 */

/**
 * Creates a memoized version of a function that only recalculates when inputs change
 * @param fn Function to memoize
 * @returns Memoized function
 */
export function memoize<T extends (...args: any[]) => any>(fn: T): T {
	let lastArgs: any[] | null = null;
	let lastResult: ReturnType<T>;

	return ((...args: Parameters<T>): ReturnType<T> => {
		// Check if arguments have changed
		if (lastArgs === null || !areArgumentsEqual(args, lastArgs)) {
			lastArgs = [...args];
			lastResult = fn(...args);
		}

		return lastResult;
	}) as T;
}

/**
 * Compare two arrays of arguments for equality
 * @param newArgs New arguments
 * @param oldArgs Old arguments
 * @returns True if arguments are equal
 */
function areArgumentsEqual(newArgs: any[], oldArgs: any[]): boolean {
	if (newArgs.length !== oldArgs.length) {
		return false;
	}

	for (let i = 0; i < newArgs.length; i++) {
		if (!isEqual(newArgs[i], oldArgs[i])) {
			return false;
		}
	}

	return true;
}

/**
 * Deep equality check for two values
 * @param a First value
 * @param b Second value
 * @returns True if values are equal
 */
function isEqual(a: any, b: any): boolean {
	// Handle primitive types
	if (a === b) {
		return true;
	}

	// Handle null/undefined
	if (a == null || b == null) {
		return a === b;
	}

	// Handle dates
	if (a instanceof Date && b instanceof Date) {
		return a.getTime() === b.getTime();
	}

	// Handle arrays
	if (Array.isArray(a) && Array.isArray(b)) {
		if (a.length !== b.length) {
			return false;
		}

		for (let i = 0; i < a.length; i++) {
			if (!isEqual(a[i], b[i])) {
				return false;
			}
		}

		return true;
	}

	// Handle objects
	if (typeof a === 'object' && typeof b === 'object') {
		const keysA = Object.keys(a);
		const keysB = Object.keys(b);

		if (keysA.length !== keysB.length) {
			return false;
		}

		for (const key of keysA) {
			if (!keysB.includes(key) || !isEqual(a[key], b[key])) {
				return false;
			}
		}

		return true;
	}

	return false;
}

/**
 * Creates a debounced function that delays invoking the provided function
 * until after the specified wait time has elapsed since the last time it was invoked
 * @param fn Function to debounce
 * @param wait Wait time in milliseconds
 * @returns Debounced function
 */
export function debounce<T extends (...args: any[]) => any>(
	fn: T,
	wait: number
): (...args: Parameters<T>) => void {
	let timeout: ReturnType<typeof setTimeout> | null = null;

	return function (...args: Parameters<T>): void {
		const later = () => {
			timeout = null;
			fn(...args);
		};

		if (timeout !== null) {
			clearTimeout(timeout);
		}

		timeout = setTimeout(later, wait);
	};
}

/**
 * Creates a throttled function that only invokes the provided function
 * at most once per every specified wait period
 * @param fn Function to throttle
 * @param wait Wait time in milliseconds
 * @returns Throttled function
 */
export function throttle<T extends (...args: any[]) => any>(
	fn: T,
	wait: number
): (...args: Parameters<T>) => void {
	let timeout: ReturnType<typeof setTimeout> | null = null;
	let lastArgs: Parameters<T> | null = null;
	let lastTime = 0;

	return function (...args: Parameters<T>): void {
		const now = Date.now();
		const remaining = wait - (now - lastTime);

		lastArgs = args;

		if (remaining <= 0 || remaining > wait) {
			if (timeout !== null) {
				clearTimeout(timeout);
				timeout = null;
			}

			lastTime = now;
			fn(...args);
		} else if (timeout === null) {
			timeout = setTimeout(() => {
				lastTime = Date.now();
				timeout = null;

				if (lastArgs !== null) {
					fn(...lastArgs);
				}
			}, remaining);
		}
	};
}
