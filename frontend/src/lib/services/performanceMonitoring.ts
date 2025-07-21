/**
 * Performance monitoring service for the frontend
 *
 * This service provides utilities for tracking API calls, cache hits/misses,
 * and performance metrics for the frontend application.
 */

import { writable, derived } from 'svelte/store';

// Performance metrics store
interface PerformanceMetrics {
	apiCalls: {
		total: number;
		byEndpoint: Record<
			string,
			{
				count: number;
				totalTimeMs: number;
				avgTimeMs: number;
				minTimeMs: number;
				maxTimeMs: number;
			}
		>;
		responseTimes: number[];
		slowOperations: Array<{
			endpoint: string;
			executionTimeMs: number;
			timestamp: string;
		}>;
	};
	cache: {
		hits: number;
		misses: number;
		byType: {
			price: { hits: number; misses: number };
			conversion: { hits: number; misses: number };
		};
	};
	rendering: {
		componentRenders: Record<string, number>;
		slowRenders: Array<{
			component: string;
			renderTimeMs: number;
			timestamp: string;
		}>;
	};
}

// Initial metrics state
const initialMetrics: PerformanceMetrics = {
	apiCalls: {
		total: 0,
		byEndpoint: {},
		responseTimes: [],
		slowOperations: []
	},
	cache: {
		hits: 0,
		misses: 0,
		byType: {
			price: { hits: 0, misses: 0 },
			conversion: { hits: 0, misses: 0 }
		}
	},
	rendering: {
		componentRenders: {},
		slowRenders: []
	}
};

// Configuration
let slowThresholdMs = 500; // Threshold for slow operations in milliseconds
let maxMetricsHistory = 100; // Maximum number of metrics to store in history

// Create the store
export const performanceMetrics = writable<PerformanceMetrics>(initialMetrics);

// Derived store for calculated metrics
export const calculatedMetrics = derived(performanceMetrics, ($metrics) => {
	// Calculate cache hit rate
	const totalCacheAccesses = $metrics.cache.hits + $metrics.cache.misses;
	const cacheHitRate = totalCacheAccesses > 0 ? $metrics.cache.hits / totalCacheAccesses : 0;

	// Calculate API response time percentiles
	const responseTimes = [...$metrics.apiCalls.responseTimes].sort((a, b) => a - b);
	const p50 = getPercentile(responseTimes, 50);
	const p90 = getPercentile(responseTimes, 90);
	const p95 = getPercentile(responseTimes, 95);
	const p99 = getPercentile(responseTimes, 99);

	return {
		cacheHitRate,
		apiResponseTimes: {
			p50,
			p90,
			p95,
			p99
		},
		slowOperationsCount: $metrics.apiCalls.slowOperations.length,
		slowRendersCount: $metrics.rendering.slowRenders.length
	};
});

/**
 * Calculate percentile from sorted array
 */
function getPercentile(sortedArray: number[], percentile: number): number | null {
	if (sortedArray.length === 0) return null;

	const index = Math.ceil((percentile / 100) * sortedArray.length) - 1;
	return sortedArray[Math.max(0, Math.min(sortedArray.length - 1, index))];
}

/**
 * Configure performance monitoring settings
 */
export function configurePerformanceMonitoring(options: {
	slowThresholdMs?: number;
	maxMetricsHistory?: number;
}): void {
	if (options.slowThresholdMs !== undefined) {
		slowThresholdMs = options.slowThresholdMs;
	}

	if (options.maxMetricsHistory !== undefined) {
		maxMetricsHistory = options.maxMetricsHistory;
	}

	console.debug(
		`Performance monitoring configured: slowThreshold=${slowThresholdMs}ms, ` +
			`maxHistory=${maxMetricsHistory}`
	);
}

/**
 * Track API call with execution time
 */
export function trackApiCall(
	endpoint: string,
	executionTimeMs: number,
	error: boolean = false
): void {
	performanceMetrics.update((metrics) => {
		// Update total API calls
		metrics.apiCalls.total++;

		// Update endpoint-specific metrics
		if (!metrics.apiCalls.byEndpoint[endpoint]) {
			metrics.apiCalls.byEndpoint[endpoint] = {
				count: 0,
				totalTimeMs: 0,
				avgTimeMs: 0,
				minTimeMs: Number.POSITIVE_INFINITY,
				maxTimeMs: 0
			};
		}

		const endpointMetrics = metrics.apiCalls.byEndpoint[endpoint];
		endpointMetrics.count++;
		endpointMetrics.totalTimeMs += executionTimeMs;
		endpointMetrics.avgTimeMs = endpointMetrics.totalTimeMs / endpointMetrics.count;
		endpointMetrics.minTimeMs = Math.min(endpointMetrics.minTimeMs, executionTimeMs);
		endpointMetrics.maxTimeMs = Math.max(endpointMetrics.maxTimeMs, executionTimeMs);

		// Add to response times history (with limit)
		metrics.apiCalls.responseTimes.push(executionTimeMs);
		if (metrics.apiCalls.responseTimes.length > maxMetricsHistory) {
			metrics.apiCalls.responseTimes.shift();
		}

		// Record slow operations
		if (executionTimeMs > slowThresholdMs) {
			metrics.apiCalls.slowOperations.push({
				endpoint,
				executionTimeMs,
				timestamp: new Date().toISOString()
			});

			// Limit history size
			if (metrics.apiCalls.slowOperations.length > maxMetricsHistory) {
				metrics.apiCalls.slowOperations.shift();
			}

			// Log slow operations to console
			console.warn(`Slow API call: ${endpoint} took ${executionTimeMs.toFixed(2)}ms`);
		}

		return metrics;
	});
}

/**
 * Track cache access (hit or miss)
 */
export function trackCacheAccess(cacheType: 'price' | 'conversion', hit: boolean): void {
	performanceMetrics.update((metrics) => {
		// Update overall cache metrics
		if (hit) {
			metrics.cache.hits++;
		} else {
			metrics.cache.misses++;
		}

		// Update cache type specific metrics
		if (hit) {
			metrics.cache.byType[cacheType].hits++;
		} else {
			metrics.cache.byType[cacheType].misses++;
		}

		return metrics;
	});
}

/**
 * Track component render time
 */
export function trackComponentRender(componentName: string, renderTimeMs: number): void {
	performanceMetrics.update((metrics) => {
		// Update component render count
		if (!metrics.rendering.componentRenders[componentName]) {
			metrics.rendering.componentRenders[componentName] = 0;
		}

		metrics.rendering.componentRenders[componentName]++;

		// Record slow renders
		if (renderTimeMs > slowThresholdMs) {
			metrics.rendering.slowRenders.push({
				component: componentName,
				renderTimeMs,
				timestamp: new Date().toISOString()
			});

			// Limit history size
			if (metrics.rendering.slowRenders.length > maxMetricsHistory) {
				metrics.rendering.slowRenders.shift();
			}

			// Log slow renders to console
			console.warn(`Slow render: ${componentName} took ${renderTimeMs.toFixed(2)}ms`);
		}

		return metrics;
	});
}

/**
 * Reset all performance metrics
 */
export function resetPerformanceMetrics(): void {
	performanceMetrics.set(initialMetrics);
}

/**
 * Create a performance monitoring wrapper for API calls
 */
export async function withPerformanceTracking<T>(
	endpoint: string,
	fn: () => Promise<T>
): Promise<T> {
	const startTime = performance.now();
	let error = false;

	try {
		return await fn();
	} catch (e) {
		error = true;
		throw e;
	} finally {
		const executionTimeMs = performance.now() - startTime;
		trackApiCall(endpoint, executionTimeMs, error);
	}
}

/**
 * Get current performance metrics
 */
export function getPerformanceMetrics(): PerformanceMetrics {
	let result: PerformanceMetrics = initialMetrics;

	performanceMetrics.subscribe((metrics) => {
		result = { ...metrics };
	})();

	return result;
}
