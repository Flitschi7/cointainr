<script lang="ts">
import { onMount } from 'svelte';
import { 
  assetCacheStatuses, 
  priceCacheStats, 
  conversionCacheStats, 
  lastCacheRefresh, 
  cacheRefreshInProgress, 
  refreshCacheStatus 
} from '$lib/stores/cacheStore';
import { cacheStatusService, CacheStatusType } from '$lib/services/cacheStatus';
import { clearPriceCache, clearConversionCache, refreshAllPrices } from '$lib/services/api';
import CacheHealthIndicator from './CacheHealthIndicator.svelte';

let refreshing = false;
let clearingPriceCache = false;
let clearingConversionCache = false;
let errorMessage: string | null = null;
let successMessage: string | null = null;

// Format the last refresh time
function formatLastRefresh(date: Date | null): string {
  if (!date) return 'Never';
  return date.toLocaleString();
}

// Handle refresh all prices
async function handleRefreshAllPrices(): Promise<void> {
  refreshing = true;
  errorMessage = null;
  successMessage = null;
  
  try {
    await refreshAllPrices();
    successMessage = 'Successfully refreshed all prices';
    // Refresh cache status after prices are refreshed
    await refreshCacheStatus();
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : 'Failed to refresh prices';
  } finally {
    refreshing = false;
  }
}

// Handle clear price cache
async function handleClearPriceCache(): Promise<void> {
  clearingPriceCache = true;
  errorMessage = null;
  successMessage = null;
  
  try {
    await clearPriceCache();
    successMessage = 'Successfully cleared price cache';
    // Refresh cache status after cache is cleared
    await refreshCacheStatus();
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : 'Failed to clear price cache';
  } finally {
    clearingPriceCache = false;
  }
}

// Handle clear conversion cache
async function handleClearConversionCache(): Promise<void> {
  clearingConversionCache = true;
  errorMessage = null;
  successMessage = null;
  
  try {
    await clearConversionCache();
    successMessage = 'Successfully cleared conversion cache';
    // Refresh cache status after cache is cleared
    await refreshCacheStatus();
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : 'Failed to clear conversion cache';
  } finally {
    clearingConversionCache = false;
  }
}

// Clear messages after a delay
function clearMessages(): void {
  setTimeout(() => {
    errorMessage = null;
    successMessage = null;
  }, 5000);
}

// Watch for message changes
$: if (errorMessage || successMessage) {
  clearMessages();
}

// Initial load
onMount(() => {
  refreshCacheStatus();
});
</script>

<div class="cache-management-panel p-4 border rounded-md">
  <h2 class="text-xl font-semibold mb-4">Cache Management</h2>
  
  <div class="mb-4">
    <CacheHealthIndicator showDetails={true} />
  </div>
  
  {#if errorMessage}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4">
      {errorMessage}
    </div>
  {/if}
  
  {#if successMessage}
    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-2 rounded mb-4">
      {successMessage}
    </div>
  {/if}
  
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
    <!-- Price Cache Stats -->
    <div class="bg-white p-4 rounded border">
      <h3 class="font-medium mb-2">Price Cache</h3>
      {#if $priceCacheStats}
        <div class="text-sm">
          <div>Total entries: {$priceCacheStats.total_entries}</div>
          <div>Fresh entries: {$priceCacheStats.fresh_entries}</div>
          <div>Stock entries: {$priceCacheStats.stock_entries}</div>
          <div>Crypto entries: {$priceCacheStats.crypto_entries}</div>
          <div>Cache age: {$priceCacheStats.cache_age_minutes} minutes</div>
        </div>
      {:else}
        <div class="text-gray-500">No price cache statistics available</div>
      {/if}
      
      <div class="mt-3">
        <button 
          class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 mr-2 text-sm"
          on:click={handleClearPriceCache}
          disabled={clearingPriceCache}
        >
          {clearingPriceCache ? 'Clearing...' : 'Clear Price Cache'}
        </button>
      </div>
    </div>
    
    <!-- Conversion Cache Stats -->
    <div class="bg-white p-4 rounded border">
      <h3 class="font-medium mb-2">Conversion Cache</h3>
      {#if $conversionCacheStats}
        <div class="text-sm">
          <div>Total entries: {$conversionCacheStats.total_entries}</div>
          <div>Fresh entries: {$conversionCacheStats.fresh_entries}</div>
          <div>Cache age: {$conversionCacheStats.cache_age_hours} hours</div>
        </div>
      {:else}
        <div class="text-gray-500">No conversion cache statistics available</div>
      {/if}
      
      <div class="mt-3">
        <button 
          class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 mr-2 text-sm"
          on:click={handleClearConversionCache}
          disabled={clearingConversionCache}
        >
          {clearingConversionCache ? 'Clearing...' : 'Clear Conversion Cache'}
        </button>
      </div>
    </div>
  </div>
  
  <div class="mb-4">
    <h3 class="font-medium mb-2">Actions</h3>
    <button 
      class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 mr-2"
      on:click={handleRefreshAllPrices}
      disabled={refreshing}
    >
      {refreshing ? 'Refreshing...' : 'Refresh All Prices'}
    </button>
    
    <button 
      class="px-3 py-1 bg-gray-500 text-white rounded hover:bg-gray-600"
      on:click={() => refreshCacheStatus()}
      disabled={$cacheRefreshInProgress}
    >
      {$cacheRefreshInProgress ? 'Refreshing...' : 'Refresh Cache Status'}
    </button>
  </div>
  
  <div>
    <h3 class="font-medium mb-2">Asset Cache Status</h3>
    <div class="max-h-64 overflow-y-auto">
      <table class="min-w-full bg-white">
        <thead>
          <tr>
            <th class="py-2 px-3 border-b text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
            <th class="py-2 px-3 border-b text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
            <th class="py-2 px-3 border-b text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th class="py-2 px-3 border-b text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cached At</th>
            <th class="py-2 px-3 border-b text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expires</th>
          </tr>
        </thead>
        <tbody>
          {#if $assetCacheStatuses.size === 0}
            <tr>
              <td colspan="5" class="py-2 px-3 text-center text-gray-500">No asset cache data available</td>
            </tr>
          {:else}
            {#each Array.from($assetCacheStatuses.values()) as status}
              {@const statusType = cacheStatusService.getCacheStatusType(status)}
              {@const statusClass = cacheStatusService.getCacheStatusClass(statusType)}
              <tr>
                <td class="py-2 px-3 border-b">{status.symbol}</td>
                <td class="py-2 px-3 border-b">{status.type}</td>
                <td class="py-2 px-3 border-b">
                  <span class={statusClass}>
                    {cacheStatusService.getCacheStatusText(statusType)}
                  </span>
                </td>
                <td class="py-2 px-3 border-b">
                  {status.cached_at ? cacheStatusService.formatCacheAge(status.cached_at) : 'N/A'}
                </td>
                <td class="py-2 px-3 border-b">
                  {status.expires_at ? cacheStatusService.formatTimeUntilExpiration(status.expires_at) : 'N/A'}
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>
  </div>
  
  <div class="mt-4 text-xs text-gray-500">
    Last cache status update: {formatLastRefresh($lastCacheRefresh)}
  </div>
</div>

<style>
  .cache-management-panel {
    background-color: #f9fafb;
  }
</style>