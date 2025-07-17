<script lang="ts">
import { cacheStatusService, type AssetCacheStatus, CacheStatusType } from '$lib/services/cacheStatus';

export let cachedAt: string | null;
export let cacheTtlMinutes: number;
export let assetType: string;
export let assetId: number | null = null;
export let showExpirationTime: boolean = false;
export let showLabel: boolean = false;

// Enhanced cache status object
let cacheStatus: AssetCacheStatus | null = null;

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
	
	return cacheStatusService.formatCacheAge(cachedAt);
}

function getStatusTooltip(): string {
	if (assetType === 'cash') return 'Cash assets do not require price updates';
	if (!cachedAt) return 'No cached data available';
	
	const statusType = cacheStatus 
		? cacheStatusService.getCacheStatusType(cacheStatus)
		: actuallyFresh ? CacheStatusType.VALID : CacheStatusType.EXPIRED;
	
	let tooltip = '';
	
	switch (statusType) {
		case CacheStatusType.FRESH:
			tooltip = '✅ Fresh data';
			break;
		case CacheStatusType.VALID:
			tooltip = '🟡 Using valid cached data';
			break;
		case CacheStatusType.EXPIRED:
			tooltip = '⚠️ Cache expired - needs refresh';
			break;
		default:
			tooltip = '❓ Unknown cache status';
	}
	
	tooltip += `\n📅 ${formatCacheTime(cachedAt, assetType)}`;
	
	if (showExpirationTime && cacheStatus?.expires_at) {
		tooltip += `\n⏱️ ${cacheStatusService.formatTimeUntilExpiration(cacheStatus.expires_at)}`;
	}
	
	if (cacheStatus?.cache_ttl_minutes) {
		tooltip += `\n⏳ Cache TTL: ${cacheStatus.cache_ttl_minutes} minutes`;
	}
	
	return tooltip;
}

function getStatusClass(): string {
	if (assetType === 'cash') return 'cache-status-na';
	
	const statusType = cacheStatus 
		? cacheStatusService.getCacheStatusType(cacheStatus)
		: actuallyFresh ? CacheStatusType.VALID : CacheStatusType.EXPIRED;
		
	return cacheStatusService.getCacheStatusClass(statusType);
}

function getStatusIcon(): string {
	if (assetType === 'cash') return '⚪'; // Not applicable
	
	if (!cachedAt) return '❓'; // Unknown status
	
	const statusType = cacheStatus 
		? cacheStatusService.getCacheStatusType(cacheStatus)
		: actuallyFresh ? CacheStatusType.VALID : CacheStatusType.EXPIRED;
		
	switch (statusType) {
		case CacheStatusType.FRESH:
			return '🟢'; // Fresh data (green circle)
		case CacheStatusType.VALID:
			return '🟡'; // Valid cached data (yellow circle)
		case CacheStatusType.EXPIRED:
			return '🔴'; // Expired cache (red circle)
		default:
			return '❓'; // Unknown status (question mark)
	}
}

function getStatusText(): string {
	if (assetType === 'cash') return 'N/A';
	
	if (!cachedAt) return 'Unknown';
	
	const statusType = cacheStatus 
		? cacheStatusService.getCacheStatusType(cacheStatus)
		: actuallyFresh ? CacheStatusType.VALID : CacheStatusType.EXPIRED;
		
	switch (statusType) {
		case CacheStatusType.FRESH:
			return 'Fresh';
		case CacheStatusType.VALID:
			return 'Cached';
		case CacheStatusType.EXPIRED:
			return 'Expired';
		default:
			return 'Unknown';
	}
}

// Load cache status if assetId is provided
async function loadCacheStatus() {
	if (assetId !== null) {
		try {
			cacheStatus = await cacheStatusService.getCacheStatusForAsset(assetId);
		} catch (error) {
			console.error('Failed to load cache status:', error);
		}
	}
}

// Initial load and refresh when assetId changes
$: if (assetId !== null) {
	loadCacheStatus();
}

$: actuallyFresh = isActuallyFresh(cachedAt, cacheTtlMinutes, assetType);
$: statusTooltip = getStatusTooltip();
$: statusClass = getStatusClass();
$: statusIcon = getStatusIcon();
$: statusText = getStatusText();
</script>

<span 
	class="cursor-help {statusClass} flex items-center" 
	title={statusTooltip}
>
	<span class="text-lg">{statusIcon}</span>
	{#if showLabel}
		<span class="ml-1 text-xs">{statusText}</span>
		{#if cachedAt && assetType !== 'cash'}
			<span class="ml-1 text-xs opacity-75">({formatCacheTime(cachedAt, assetType)})</span>
		{/if}
	{/if}
</span>

<style>
	.cache-status-fresh {
		color: #10b981; /* Emerald-500 */
	}
	
	.cache-status-valid {
		color: #f59e0b; /* Amber-500 */
	}
	
	.cache-status-expired {
		color: #ef4444; /* Red-500 */
	}
	
	.cache-status-unknown {
		color: #9ca3af; /* Gray-400 */
	}
	
	.cache-status-na {
		color: #9ca3af; /* Gray-400 */
		opacity: 0.5;
	}
</style>
