/**
 * Request deduplication service
 *
 * This service prevents multiple simultaneous requests for the same data
 * by maintaining a map of pending requests and returning the same promise
 * for identical requests.
 */

// Map to store pending requests with timestamps
const pendingRequests = new Map<string, { promise: Promise<any>; timestamp: number }>();

// Cleanup interval to remove old entries
const CLEANUP_INTERVAL = 30000; // 30 seconds
const MAX_PENDING_TIME = 60000; // 1 minute

// Cleanup old pending requests periodically
setInterval(() => {
	const now = Date.now();
	for (const [key, entry] of pendingRequests.entries()) {
		if (now - entry.timestamp > MAX_PENDING_TIME) {
			pendingRequests.delete(key);
		}
	}
}, CLEANUP_INTERVAL);

/**
 * Execute a function with request deduplication
 * @param key Unique key for the request
 * @param fn Function to execute
 * @returns Promise that resolves to the function result
 */
export async function withDeduplication<T>(key: string, fn: () => Promise<T>): Promise<T> {
	// Check if there's already a pending request for this key
	const existing = pendingRequests.get(key);
	if (existing) {
		console.debug(`Deduplicating request for key: ${key}`);
		return existing.promise as Promise<T>;
	}

	// Create a new request
	const promise = fn().finally(() => {
		// Remove from pending requests when completed
		pendingRequests.delete(key);
	});

	// Store the promise with timestamp
	pendingRequests.set(key, {
		promise,
		timestamp: Date.now()
	});

	return promise;
}

/**
 * Clear all pending requests (useful for cleanup)
 */
export function clearPendingRequests(): void {
	pendingRequests.clear();
}

/**
 * Get the number of pending requests
 */
export function getPendingRequestCount(): number {
	return pendingRequests.size;
}

/**
 * Get all pending request keys (for debugging)
 */
export function getPendingRequestKeys(): string[] {
	return Array.from(pendingRequests.keys());
}
