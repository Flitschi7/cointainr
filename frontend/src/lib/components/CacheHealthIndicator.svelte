<script lang="ts">
import { cacheHealth } from '$lib/stores/cacheStore';
import TransitionWrapper from './TransitionWrapper.svelte';
import SkeletonLoader from './SkeletonLoader.svelte';

export let showDetails: boolean = false;

// Memoized values to prevent unnecessary calculations
let healthStatusClass: string;
let healthStatusText: string;
let assetCacheHealthClass: string;
let priceCacheHealthClass: string;
let conversionCacheHealthClass: string;

// Helper function to get health status class - memoized to prevent recalculation
function getHealthStatusClass(status: string): string {
    switch (status) {
        case 'good':
            return 'bg-green-500';
        case 'warning':
            return 'bg-yellow-500';
        case 'critical':
            return 'bg-red-500';
        default:
            return 'bg-gray-500';
    }
}

// Helper function to get health status text - memoized to prevent recalculation
function getHealthStatusText(status: string): string {
    switch (status) {
        case 'good':
            return 'Good';
        case 'warning':
            return 'Warning';
        case 'critical':
            return 'Critical';
        default:
            return 'Unknown';
    }
}

// Helper function to get health class based on percentage
function getHealthClassForPercentage(percentage: number): string {
    if (percentage > 80) return 'bg-green-500';
    if (percentage > 50) return 'bg-yellow-500';
    return 'bg-red-500';
}

// Update memoized values when cacheHealth changes
$: if ($cacheHealth && $cacheHealth.status !== undefined) {
    healthStatusClass = getHealthStatusClass($cacheHealth.status);
    healthStatusText = getHealthStatusText($cacheHealth.status);
    
    // Pre-calculate health classes for better performance
    assetCacheHealthClass = getHealthClassForPercentage($cacheHealth.assetCacheHealthPercentage);
    priceCacheHealthClass = getHealthClassForPercentage($cacheHealth.priceHealth);
    conversionCacheHealthClass = getHealthClassForPercentage($cacheHealth.conversionHealth);
}
</script>

<div class="cache-health-indicator">
    <TransitionWrapper isLoading={!$cacheHealth || $cacheHealth.status === undefined} transitionType="fade">
        <svelte:fragment slot="loading">
            <div class="flex items-center gap-2">
                <SkeletonLoader type="rectangle" width="8rem" height="1.25rem" />
                <SkeletonLoader type="rectangle" width="4rem" height="1rem" />
            </div>
        </svelte:fragment>
        
        {#if $cacheHealth && $cacheHealth.status !== undefined}
            <div class="flex items-center gap-2">
                <div class="flex items-center">
                    <div class={`w-3 h-3 rounded-full ${getHealthStatusClass($cacheHealth.status)}`}></div>
                    <span class="ml-2 font-medium">Cache Health: {getHealthStatusText($cacheHealth.status)}</span>
                </div>
                
                <div class="text-sm text-gray-400">
                    {Math.round($cacheHealth.overallHealth)}% overall
                </div>
            </div>
            
            {#if showDetails}
                <div class="mt-2 grid grid-cols-3 gap-4 text-sm">
                    <div class="flex flex-col">
                        <span class="text-gray-400">Asset Cache</span>
                        <div class="flex items-center mt-1">
                            <div class="w-full bg-gray-700 rounded-full h-2">
                                <div 
                                    class="h-2 rounded-full {assetCacheHealthClass}" 
                                    style="width: {$cacheHealth.assetCacheHealthPercentage}%"
                                ></div>
                            </div>
                            <span class="ml-2">{Math.round($cacheHealth.assetCacheHealthPercentage)}%</span>
                        </div>
                    </div>
                    
                    <div class="flex flex-col">
                        <span class="text-gray-400">Price Cache</span>
                        <div class="flex items-center mt-1">
                            <div class="w-full bg-gray-700 rounded-full h-2">
                                <div 
                                    class="h-2 rounded-full {priceCacheHealthClass}" 
                                    style="width: {$cacheHealth.priceHealth}%"
                                ></div>
                            </div>
                            <span class="ml-2">{Math.round($cacheHealth.priceHealth)}%</span>
                        </div>
                    </div>
                    
                    <div class="flex flex-col">
                        <span class="text-gray-400">Conversion Cache</span>
                        <div class="flex items-center mt-1">
                            <div class="w-full bg-gray-700 rounded-full h-2">
                                <div 
                                    class="h-2 rounded-full {conversionCacheHealthClass}" 
                                    style="width: {$cacheHealth.conversionHealth}%"
                                ></div>
                            </div>
                            <span class="ml-2">{Math.round($cacheHealth.conversionHealth)}%</span>
                        </div>
                    </div>
                </div>
            {/if}
        {/if}
    </TransitionWrapper>
</div>

<style>
    .cache-health-indicator {
        padding: 0.75rem;
        border-radius: 0.375rem;
        background-color: rgba(255, 255, 255, 0.05);
    }
</style>