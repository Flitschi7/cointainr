import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// Configure static adapter for FastAPI serving
		adapter: adapter({
			// Output directory for built files - using 'build' directory for clarity
			pages: 'build',
			assets: 'build',
			// Fallback for SPA routing - serve index.html for all routes
			fallback: 'index.html',
			// Disable precompression as FastAPI will handle it
			precompress: false,
			// Enable strict mode for better error detection
			strict: true
		}),

		// Configure prerendering to handle all discoverable routes
		prerender: {
			// How to handle missing IDs in prerendering
			handleMissingId: 'warn',
			// Prerender all routes for better performance
			entries: ['*'],
			// Ensure all pages are prerendered
			handleHttpError: ({ path, referrer, message }) => {
				// Log prerendering errors but don't fail the build
				console.warn(`Prerendering error for ${path} (referrer: ${referrer}): ${message}`);
				return;
			}
		},

		// Configure paths for proper asset serving through FastAPI
		paths: {
			base: '',
			assets: ''
		}
	}
};

export default config;
