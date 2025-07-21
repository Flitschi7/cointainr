<script lang="ts">
import { cacheHealth, lastCacheRefresh } from '$lib/stores/cacheStore';
// Removed CacheHealthIndicator - too complex for users

export let lastRefreshTime: Date | null = null;

// Format the last refresh time
function formatLastRefresh(date: Date | null): string {
    if (!date) return 'Never';
    
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Determine if a refresh is recommended based on cache health
$: refreshRecommended = $cacheHealth.overallHealth < 70;
</script>

<div class="cache-status-banner bg-surface rounded-lg p-3 mb-4 flex items-center justify-between">
    <div class="flex items-center gap-4">
        <div class="text-sm">
            <span class="text-gray-400">Last refresh:</span>
            <span class="ml-1 font-mono">{formatLastRefresh(lastRefreshTime || $lastCacheRefresh)}</span>
        </div>
    </div>
    
    {#if refreshRecommended}
        <div class="text-yellow-500 text-sm flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <span>Cache health low - refresh recommended</span>
        </div>
    {/if}
</div>