
<script>
  import "../app.css";
  import CacheStatusProvider from '$lib/components/CacheStatusProvider.svelte';
</script>

<CacheStatusProvider>
  <slot />
</CacheStatusProvider>