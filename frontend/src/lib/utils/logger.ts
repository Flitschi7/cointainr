/**
 * Centralized logging utility with environment-aware output
 *
 * This utility provides consistent logging across the application with
 * automatic production/development detection to minimize console noise.
 */

// Environment detection using Vite's import.meta.env (browser-compatible)
const isDev = import.meta.env.DEV;
const isVerbose = isDev && !import.meta.env.VITE_QUIET_LOGS; // Set VITE_QUIET_LOGS=true to reduce dev logs

/**
 * Development-only logger that respects environment settings
 */
export const devLog = {
	info: (...args: any[]) => {
		if (isVerbose) console.log(...args);
	},

	warn: (...args: any[]) => {
		if (isDev) console.warn(...args); // Always show warnings in dev
	},

	error: (...args: any[]) => {
		// Always log errors, even in production
		console.error(...args);
	},

	debug: (...args: any[]) => {
		if (isVerbose) console.debug(...args);
	},

	group: (label: string) => {
		if (isVerbose) console.group(label);
	},

	groupEnd: () => {
		if (isVerbose) console.groupEnd();
	}
};

/**
 * Performance-focused logger for development profiling
 */
export const perfLog = {
	time: (label: string) => {
		if (isVerbose) console.time(label);
	},

	timeEnd: (label: string) => {
		if (isVerbose) console.timeEnd(label);
	}
};

/**
 * Legacy support - conditional logging function
 */
export const conditionalLog = isVerbose ? console.log : () => {};

/**
 * Environment detection flags for inline conditionals
 */
export { isDev, isVerbose };
