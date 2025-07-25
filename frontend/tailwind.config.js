/** @type {import('tailwindcss').Config} */
module.exports = {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				primary: '#00C896',
				background: '#1E1E2F',
				surface: '#2A2F45',
				'text-light': '#F0F4F8',
				profit: '#2ECC71',
				loss: '#E74C3C',
				gold: '#D4AF37'
			},
			fontFamily: {
				sans: ['Inter', 'sans-serif'],
				headline: ['Space Grotesk', 'sans-serif'],
				mono: ['JetBrains Mono', 'monospace']
			}
		}
	},
	plugins: []
};
