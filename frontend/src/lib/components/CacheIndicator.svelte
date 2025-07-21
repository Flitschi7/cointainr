<script lang="ts">
export let isCached: boolean = false;
export let lastUpdated: string | null = null;
export let isStale: boolean = false;
export let showLabel: boolean = false;
export let showTimestamp: boolean = false;

// Memoized values to prevent unnecessary calculations
let statusIcon: string;
let statusText: string;
let statusClass: string;
let tooltipText: string;
let formattedTime: string;

// Format the timestamp for display - memoized to prevent recalculation
function formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    
    // Convert to appropriate time unit
    if (diffMs < 60000) {
        // Less than a minute
        const seconds = Math.floor(diffMs / 1000);
        return `${seconds} second${seconds !== 1 ? 's' : ''} ago`;
    } else if (diffMs < 3600000) {
        // Less than an hour
        const minutes = Math.floor(diffMs / 60000);
        return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    } else if (diffMs < 86400000) {
        // Less than a day
        const hours = Math.floor(diffMs / 3600000);
        return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else {
        // Days or more
        const days = Math.floor(diffMs / 86400000);
        return `${days} day${days !== 1 ? 's' : ''} ago`;
    }
}

// Combine all status calculations into a single reactive statement
// to reduce the number of reactive statements and prevent unnecessary recalculations
$: {
    // Get the appropriate icon and color based on cache status
    if (!isCached) {
        statusIcon = '🟢'; // Fresh data (green circle)
        statusText = 'Fresh';
        statusClass = 'cache-fresh';
        tooltipText = 'Fresh data from API';
    } else if (isStale) {
        statusIcon = '🔴'; // Stale/expired cache (red circle)
        statusText = 'Stale';
        statusClass = 'cache-stale';
        tooltipText = 'Stale cached data - refresh recommended';
    } else {
        statusIcon = '🟡'; // Valid cached data (yellow circle)
        statusText = 'Cached';
        statusClass = 'cache-valid';
        tooltipText = 'Valid cached data';
    }
    
    // Add timestamp to tooltip if available
    if (lastUpdated) {
        formattedTime = formatTimestamp(lastUpdated);
        tooltipText += `\nLast updated: ${formattedTime}`;
    } else {
        formattedTime = 'Unknown';
    }
}
</script>

<span class="cache-indicator {statusClass}" title={tooltipText}>
    <span class="icon">{statusIcon}</span>
    {#if showLabel}
        <span class="label">{statusText}</span>
    {/if}
    {#if showTimestamp && lastUpdated}
        <span class="timestamp">{formattedTime}</span>
    {/if}
</span>

<style>
    .cache-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.875rem;
        cursor: help;
    }
    
    .icon {
        font-size: 1em;
    }
    
    .label {
        font-weight: 500;
    }
    
    .timestamp {
        font-size: 0.75rem;
        opacity: 0.75;
    }
    
    .cache-fresh {
        color: #10b981; /* Emerald-500 */
    }
    
    .cache-valid {
        color: #f59e0b; /* Amber-500 */
    }
    
    .cache-stale {
        color: #ef4444; /* Red-500 */
    }
</style>