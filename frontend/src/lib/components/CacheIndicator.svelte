<script lang="ts">
export let cached: boolean = false;
export let source: string = '';
export let fetched_at: string = '';
export let size: 'sm' | 'md' = 'sm';

function formatTime(dateStr: string): string {
	if (!dateStr) return '';
	try {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / (1000 * 60));
		
		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		
		const diffHours = Math.floor(diffMins / 60);
		if (diffHours < 24) return `${diffHours}h ago`;
		
		const diffDays = Math.floor(diffHours / 24);
		return `${diffDays}d ago`;
	} catch {
		return '';
	}
}

$: timeAgo = formatTime(fetched_at);
$: tooltipText = `${cached ? 'Cached' : 'Fresh'} data from ${source}${timeAgo ? ` (${timeAgo})` : ''}`;
</script>

{#if cached || source}
	<span 
		class="inline-flex items-center ml-1 text-gray-400"
		class:text-xs={size === 'sm'}
		class:text-sm={size === 'md'}
		title={tooltipText}
	>
		{#if cached}
			📋
		{:else}
			🔄
		{/if}
	</span>
{/if}
