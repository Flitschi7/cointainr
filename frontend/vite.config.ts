import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],

	// Development server configuration
	server: {
		port: 5173,
		host: true, // Allow external connections
		proxy: {
			// Proxy API requests to backend during development
			'/api': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true,
				secure: false
			}
		}
	},

	// Build configuration for consistent asset naming
	build: {
		rollupOptions: {
			output: {
				assetFileNames: '_app/immutable/assets/[name]-[hash][extname]',
				chunkFileNames: '_app/immutable/chunks/[name]-[hash].js',
				entryFileNames: '_app/immutable/entry/[name]-[hash].js'
			}
		}
	}
});
