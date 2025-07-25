/**
 * Global error handling utilities for the application
 *
 * This module provides functions for handling errors consistently across the application,
 * including error logging, categorization, and user-friendly error messages.
 */

/**
 * Error categories for better error handling
 */
export enum ErrorCategory {
	NETWORK = 'network',
	API = 'api',
	VALIDATION = 'validation',
	AUTHENTICATION = 'authentication',
	AUTHORIZATION = 'authorization',
	RATE_LIMIT = 'rate-limit',
	SERVER = 'server',
	CLIENT = 'client',
	UNKNOWN = 'unknown'
}

/**
 * Enhanced error interface with additional context
 */
export interface EnhancedError extends Error {
	category?: ErrorCategory;
	status?: number;
	statusText?: string;
	originalMessage?: string;
	timestamp?: string;
	data?: any;
	isNetworkError?: boolean;
	retryable?: boolean;
}

/**
 * Categorize an error based on its properties
 * @param error Error to categorize
 * @returns Error category
 */
export function categorizeError(error: any): ErrorCategory {
	// Check for network errors
	if (error instanceof TypeError && error.message.includes('network')) {
		return ErrorCategory.NETWORK;
	}

	// Check for API errors with status codes
	if (error.status) {
		if (error.status === 401) {
			return ErrorCategory.AUTHENTICATION;
		} else if (error.status === 403) {
			return ErrorCategory.AUTHORIZATION;
		} else if (error.status === 429) {
			return ErrorCategory.RATE_LIMIT;
		} else if (error.status >= 400 && error.status < 500) {
			return ErrorCategory.CLIENT;
		} else if (error.status >= 500) {
			return ErrorCategory.SERVER;
		}
	}

	// Check for validation errors
	if (
		error.message &&
		(error.message.includes('validation') ||
			error.message.includes('invalid') ||
			error.message.includes('required'))
	) {
		return ErrorCategory.VALIDATION;
	}

	// Default to unknown
	return ErrorCategory.UNKNOWN;
}

/**
 * Check if an error is retryable
 * @param error Error to check
 * @returns True if the error is retryable
 */
export function isRetryableError(error: any): boolean {
	// Network errors are retryable
	if (error instanceof TypeError && error.message.includes('network')) {
		return true;
	}

	// Rate limit errors are retryable
	if (error.status === 429) {
		return true;
	}

	// Server errors are retryable
	if (error.status && error.status >= 500 && error.status < 600) {
		return true;
	}

	// Explicitly marked as retryable
	if (error.retryable === true) {
		return true;
	}

	// Default to not retryable
	return false;
}

/**
 * Get a user-friendly error message based on the error
 * @param error Error to get message for
 * @returns User-friendly error message
 */
export function getUserFriendlyErrorMessage(error: any): string {
	const category = error.category || categorizeError(error);

	switch (category) {
		case ErrorCategory.NETWORK:
			return 'Network connection error. Please check your internet connection.';
		case ErrorCategory.AUTHENTICATION:
			return 'Authentication error. Please log in again.';
		case ErrorCategory.AUTHORIZATION:
			return 'You do not have permission to perform this action.';
		case ErrorCategory.RATE_LIMIT:
			return 'Rate limit exceeded. Please try again later.';
		case ErrorCategory.VALIDATION:
			return 'Invalid input. Please check your data and try again.';
		case ErrorCategory.SERVER:
			return 'Server error. Our team has been notified.';
		case ErrorCategory.CLIENT:
			return 'Request error. Please try again.';
		default:
			return error.message || 'An unexpected error occurred.';
	}
}

/**
 * Log an error with additional context
 * @param error Error to log
 * @param context Additional context for the error
 */
export function logError(error: any, context?: string): void {
	const category = error.category || categorizeError(error);
	const timestamp = new Date().toISOString();

	console.error(
		`[${timestamp}] ${context ? `[${context}] ` : ''}[${category}] Error:`,
		error.originalMessage || error.message,
		error
	);
}

/**
 * Enhance an error with additional context and information
 * @param error Original error
 * @param friendlyMessage User-friendly error message
 * @returns Enhanced error object
 */
export function enhanceError(error: any, friendlyMessage?: string): EnhancedError {
	// Create a new error with the friendly message
	const enhancedError: EnhancedError = new Error(
		friendlyMessage || getUserFriendlyErrorMessage(error)
	);

	// Copy properties from the original error
	if (error instanceof Error) {
		enhancedError.originalMessage = error.message;
		enhancedError.stack = error.stack;
		enhancedError.name = error.name;
	}

	// Add additional context
	enhancedError.timestamp = new Date().toISOString();
	enhancedError.category = categorizeError(error);
	enhancedError.retryable = isRetryableError(error);

	// Add network-specific information
	if (error instanceof TypeError && error.message.includes('network')) {
		enhancedError.isNetworkError = true;
	}

	// Add API-specific information
	if (error.status) {
		enhancedError.status = error.status;
		enhancedError.statusText = error.statusText;
		enhancedError.data = error.data;
	}

	return enhancedError;
}

/**
 * Initialize global error handlers
 */
export function initializeGlobalErrorHandlers(): void {
	// Handle unhandled promise rejections
	window.addEventListener('unhandledrejection', (event) => {
		const error = event.reason;
		logError(error, 'Unhandled Promise Rejection');
	});

	// Handle uncaught exceptions
	window.addEventListener('error', (event) => {
		const error = event.error;
		logError(error, 'Uncaught Exception');
	});
}
