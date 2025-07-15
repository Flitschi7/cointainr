<script lang="ts">
export let cachedAt: string | null;
export let cacheTtlMinutes: number;
export let assetType: string;

// Calculate freshness on frontend to handle timezone properly
function isActuallyFresh(cachedAt: string | null, ttlMinutes: number, assetType: string): boolean {
	// Cash assets are always "fresh" since they don't need price updates
	if (assetType === 'cash') return true;
	
	if (!cachedAt) return false;
	
	const cacheTime = new Date(cachedAt);
	const now = new Date();
	const diffMs = now.getTime() - cacheTime.getTime();
	const diffMins = diffMs / (1000 * 60);
	
	return diffMins <= ttlMinutes;
}

function formatCacheTime(cachedAt: string | null, assetType: string): string {
	if (assetType === 'cash') return 'Cash assets do not require price updates';
	if (!cachedAt) return 'No cached data';
	
	// Parse the UTC timestamp from backend
	const date = new Date(cachedAt);
	const now = new Date();
	
	// Calculate actual time difference (this handles timezone automatically)
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / (1000 * 60));
	
	if (diffMins < 1) return 'Cached just now';
	if (diffMins < 60) return `Cached ${diffMins} min ago`;
	
	const diffHours = Math.floor(diffMins / 60);
	if (diffHours < 24) return `Cached ${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
	
	// For display, convert to local time
	return `Cached on ${date.toLocaleDateString()} at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

$: actuallyFresh = isActuallyFresh(cachedAt, cacheTtlMinutes, assetType);
</script>

<span 
	class="cursor-help text-lg" 
	title={formatCacheTime(cachedAt, assetType)}
>
	{actuallyFresh ? '🟢' : '🔴'}
</span>
