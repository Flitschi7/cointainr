/**
 * Utility functions for handling API retries with exponential backoff
 */

/**
 * Options for retry functionality
 */
export interface RetryOptions {
	/** Maximum number of retry attempts */
	maxRetries?: number;
	/** Initial delay in milliseconds */
	initialDelay?: number;
	/** Maximum delay in milliseconds */
	maxDelay?: number;
	/** Backoff factor (how quickly the delay increases) */
	backoffFactor?: number;
	/** Function to determine if an error is retryable */
	isRetryable?: (error: any) => boolean;
	/** Callback function to execute before each retry */
	onRetry?: (attempt: number, delay: number, error: any) => void;
}

/**
 * Default retry options
 */
const defaultRetryOptions: Required<RetryOptions> = {
	maxRetries: 3,
	initialDelay: 1000, // 1 second
	maxDelay: 30000, // 30 seconds
	backoffFactor: 2,
	isRetryable: (error: any) => {
		// By default, retry network errors and 5xx server errors
		if (error instanceof TypeError && error.message.includes('network')) {
			return true;
		}

		if (error.status && error.status >= 500 && error.status < 600) {
			return true;
		}

		// Don't retry 4xx client errors (except 429 Too Many Requests)
		if (error.status && error.status === 429) {
			return true;
		}

		return false;
	},
	onRetry: (attempt, delay, error) => {
		console.warn(`Retry attempt ${attempt} after ${delay}ms due to error:`, error);
	}
};

/**
 * Sleep for a specified duration
 * @param ms Milliseconds to sleep
 * @returns Promise that resolves after the specified duration
 */
const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Calculate exponential backoff delay
 * @param attempt Current attempt number (0-based)
 * @param options Retry options
 * @returns Delay in milliseconds
 */
export function calculateBackoffDelay(
	attempt: number,
	options: Partial<RetryOptions> = {}
): number {
	const { initialDelay, backoffFactor, maxDelay } = { ...defaultRetryOptions, ...options };

	// Calculate exponential backoff with jitter
	const exponentialDelay = initialDelay * Math.pow(backoffFactor, attempt);
	const jitter = Math.random() * 0.3 * exponentialDelay; // Add up to 30% jitter
	const delay = Math.min(exponentialDelay + jitter, maxDelay);

	return Math.floor(delay);
}

/**
 * Execute a function with retry logic and exponential backoff
 * @param fn Function to execute
 * @param options Retry options
 * @returns Promise that resolves with the function result or rejects after all retries fail
 */
export async function withRetry<T>(fn: () => Promise<T>, options: RetryOptions = {}): Promise<T> {
	const mergedOptions: Required<RetryOptions> = { ...defaultRetryOptions, ...options };
	const { maxRetries, isRetryable, onRetry } = mergedOptions;

	let lastError: any;

	for (let attempt = 0; attempt <= maxRetries; attempt++) {
		try {
			// First attempt or retry
			return await fn();
		} catch (error) {
			lastError = error;

			// Check if we should retry
			const shouldRetry = attempt < maxRetries && isRetryable(error);

			if (!shouldRetry) {
				break;
			}

			// Calculate delay for next retry
			const delay = calculateBackoffDelay(attempt, mergedOptions);

			// Execute onRetry callback
			if (onRetry) {
				onRetry(attempt + 1, delay, error);
			}

			// Wait before retrying
			await sleep(delay);
		}
	}

	// If we get here, all retries failed
	throw lastError;
}

/**
 * Create a retryable version of a function
 * @param fn Function to make retryable
 * @param options Retry options
 * @returns A new function that includes retry logic
 */
export function createRetryableFunction<T extends (...args: any[]) => Promise<any>>(
	fn: T,
	options: RetryOptions = {}
): T {
	return ((...args: Parameters<T>): ReturnType<T> => {
		return withRetry(() => fn(...args), options) as ReturnType<T>;
	}) as T;
}
