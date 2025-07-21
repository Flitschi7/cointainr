<script lang="ts">
import { onMount, onDestroy } from 'svelte';
import { performanceMetrics, calculatedMetrics, resetPerformanceMetrics } from '$lib/services/performanceMonitoring';
import TransitionWrapper from './TransitionWrapper.svelte';
import CardSkeleton from './CardSkeleton.svelte';

export let compact: boolean = false;
export let showResetButton: boolean = true;

let isResetting = false;

// Format a number with 2 decimal places
function formatNumber(value: number | null): string {
    if (value === null) return 'N/A';
    return value.toFixed(2);
}

// Format a percentage
function formatPercentage(value: number | null): string {
    if (value === null) return 'N/A';
    return `${(value * 100).toFixed(1)}%`;
}

// Handle reset button click
async function handleReset() {
    isResetting = true;
    resetPerformanceMetrics();
    setTimeout(() => {
        isResetting = false;
    }, 500);
}

// Auto-refresh metrics every 5 seconds
let refreshInterval: ReturnType<typeof setInterval>;

onMount(() => {
    refreshInterval = setInterval(() => {
        // This will trigger a reactive update of the metrics
        performanceMetrics.update(m => m);
    }, 5000);
});

onDestroy(() => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
</script>

<div class="performance-monitor bg-surface rounded-lg p-4 shadow-md">
    <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">Performance Metrics</h2>
        
        {#if showResetButton}
            <button 
                class="bg-red-500 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                on:click={handleReset}
                disabled={isResetting}
            >
                {#if isResetting}
                    <span>Resetting...</span>
                {:else}
                    <span>Reset Metrics</span>
                {/if}
            </button>
        {/if}
    </div>
    
    <TransitionWrapper isLoading={false} transitionType="fade">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- API Metrics -->
            <div class="bg-background rounded p-3">
                <h3 class="text-sm font-medium mb-2">API Calls</h3>
                <div class="text-xs space-y-1">
                    <div>Total calls: {$performanceMetrics.apiCalls.total}</div>
                    <div>Avg response time: {formatNumber($calculatedMetrics.apiResponseTimes.p50 || 0)} ms</div>
                    <div>P90 response time: {formatNumber($calculatedMetrics.apiResponseTimes.p90 || 0)} ms</div>
                    <div>Slow operations: {$calculatedMetrics.slowOperationsCount}</div>
                </div>
            </div>
            
            <!-- Cache Metrics -->
            <div class="bg-background rounded p-3">
                <h3 class="text-sm font-medium mb-2">Cache Performance</h3>
                <div class="text-xs space-y-1">
                    <div>Hit rate: {formatPercentage($calculatedMetrics.cacheHitRate)}</div>
                    <div>Hits: {$performanceMetrics.cache.hits}</div>
                    <div>Misses: {$performanceMetrics.cache.misses}</div>
                </div>
            </div>
            
            {#if !compact}
                <!-- Slow Operations -->
                <div class="bg-background rounded p-3 md:col-span-2">
                    <h3 class="text-sm font-medium mb-2">Slow Operations</h3>
                    {#if $performanceMetrics.apiCalls.slowOperations.length > 0}
                        <div class="text-xs max-h-32 overflow-y-auto">
                            <table class="w-full">
                                <thead>
                                    <tr class="text-left">
                                        <th class="pb-1">Endpoint</th>
                                        <th class="pb-1">Time (ms)</th>
                                        <th class="pb-1">Timestamp</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {#each $performanceMetrics.apiCalls.slowOperations.slice().reverse() as op}
                                        <tr>
                                            <td class="pr-2 truncate max-w-[150px]">{op.endpoint}</td>
                                            <td class="pr-2">{op.executionTimeMs.toFixed(2)}</td>
                                            <td class="text-gray-400">{new Date(op.timestamp).toLocaleTimeString()}</td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {:else}
                        <div class="text-xs text-gray-400">No slow operations recorded</div>
                    {/if}
                </div>
                
                <!-- Cache Details -->
                <div class="bg-background rounded p-3">
                    <h3 class="text-sm font-medium mb-2">Price Cache</h3>
                    <div class="text-xs space-y-1">
                        <div>Hits: {$performanceMetrics.cache.byType.price.hits}</div>
                        <div>Misses: {$performanceMetrics.cache.byType.price.misses}</div>
                        <div>Hit rate: {formatPercentage(
                            $performanceMetrics.cache.byType.price.hits / 
                            Math.max(1, $performanceMetrics.cache.byType.price.hits + $performanceMetrics.cache.byType.price.misses)
                        )}</div>
                    </div>
                </div>
                
                <div class="bg-background rounded p-3">
                    <h3 class="text-sm font-medium mb-2">Conversion Cache</h3>
                    <div class="text-xs space-y-1">
                        <div>Hits: {$performanceMetrics.cache.byType.conversion.hits}</div>
                        <div>Misses: {$performanceMetrics.cache.byType.conversion.misses}</div>
                        <div>Hit rate: {formatPercentage(
                            $performanceMetrics.cache.byType.conversion.hits / 
                            Math.max(1, $performanceMetrics.cache.byType.conversion.hits + $performanceMetrics.cache.byType.conversion.misses)
                        )}</div>
                    </div>
                </div>
            {/if}
        </div>
    </TransitionWrapper>
</div>

<style>
    .performance-monitor {
        font-family: 'Inter', sans-serif;
    }
</style>