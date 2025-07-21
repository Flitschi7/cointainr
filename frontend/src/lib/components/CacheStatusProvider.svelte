<script lang="ts">
  /**
   * Cache Status Provider Component
   * 
   * This component manages the global cache status and provides it to all child components
   * through the Svelte context API. This prevents excessive API calls for cache status.
   */
  import { onMount, onDestroy, setContext } from 'svelte';
  import { refreshAssetCacheStatus, assetCacheStatus } from '$lib/stores/assetStatusStore';
  
  // Update interval in milliseconds
  const UPDATE_INTERVAL = 5000; // 5 seconds
  
  let intervalId: ReturnType<typeof setInterval>;
  
  // Set up context for child components
  setContext('cacheStatus', {
    assetCacheStatus,
    refreshAssetCacheStatus
  });
  
  onMount(() => {
    // Initial fetch
    refreshAssetCacheStatus();
    
    // Set up periodic refresh
    intervalId = setInterval(() => {
      if (document.visibilityState === 'visible') {
        refreshAssetCacheStatus();
      }
    }, UPDATE_INTERVAL);
    
    // Refresh when tab becomes visible
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refreshAssetCacheStatus();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  });
  
  onDestroy(() => {
    if (intervalId) {
      clearInterval(intervalId);
    }
  });
</script>

<!-- This component doesn't render anything, it just provides context -->
<slot></slot>