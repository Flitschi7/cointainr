
<script>
	import '../app.css';
	import CacheStatusProvider from '$lib/components/CacheStatusProvider.svelte';
	// Read Umami env variables (Vite exposes them as import.meta.env)
	const umamiId = import.meta.env.VITE_UMAMI_WEBSITE_ID;
	const umamiUrl = import.meta.env.VITE_UMAMI_SCRIPT_URL;
</script>

<svelte:head>
	{#if umamiId && umamiUrl}
		<script defer src={umamiUrl} data-website-id={umamiId}></script>
	{/if}
</svelte:head>

<CacheStatusProvider>
	<slot />
</CacheStatusProvider>
