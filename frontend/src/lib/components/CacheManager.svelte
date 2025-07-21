<script lang="ts">
import { onMount } from 'svelte';
import { cacheHealth, priceCacheStats, conversionCacheStats } from '$lib/stores/cacheStore';
import { refreshAssetCacheStatus } from '$lib/stores/assetStatusStore';
import CacheHealthIndicator from './CacheHealthIndicator.svelte';
import ErrorState from './ErrorState.svelte';
import LoadingIndicator from './LoadingIndicator.svelte';
import TransitionWrapper from './TransitionWrapper.svelte';
import CardSkeleton from './CardSkeleton.svelte';
import * as apiWithRetry from '$lib/services/apiWithRetry';

export let compact: boolean = false;

let isRefreshing = false;
let isClearingPriceCache = false;
let isClearingConversionCache = false;
let message: { type: 'success' | 'error', text: string, details?: string } | null = null;
let retryCount = {
    refresh: 0,
    clearPrice: 0,
    clearConversion: 0
};
const maxRetries = 3;

// Memoized values for retry handler
let retryHandler: (() => Promise<void>) | null = null;

// Memoize the retry handler based on the error message
$: if (message?.type === 'error') {
    if (message.text.includes('refresh')) {
        retryHandler = retryRefreshAll;
    } else if (message.text.includes('price cache')) {
        retryHandler = retryClearPriceCache;
    } else if (message.text.includes('conversion cache')) {
        retryHandler = retryClearConversionCache;
    } else {
        retryHandler = null;
    }
} else {
    retryHandler = null;
}

// Debounced refresh function to prevent excessive API calls
let refreshTimeout: ReturnType<typeof setTimeout> | null = null;
function debouncedRefreshStatus() {
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
    }
    
    refreshTimeout = setTimeout(() => {
        refreshAssetCacheStatus();
        refreshTimeout = null;
    }, 300);
}

async function handleRefreshAll() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    message = null;
    
    try {
        await apiWithRetry.refreshAllPrices();
        await refreshAssetCacheStatus();
        message = { type: 'success', text: 'Successfully refreshed all prices' };
        retryCount.refresh = 0; // Reset retry count on success
    } catch (error: any) {
        console.error('Failed to refresh prices:', error);
        
        // Enhanced error handling with detailed information
        const errorMessage = error.message || 'Failed to refresh prices';
        const errorDetails = error.originalMessage || error.statusText || '';
        
        message = { 
            type: 'error', 
            text: errorMessage,
            details: errorDetails
        };
    } finally {
        isRefreshing = false;
        clearMessageAfterDelay();
    }
}

async function handleClearPriceCache() {
    if (isClearingPriceCache) return;
    
    isClearingPriceCache = true;
    message = null;
    
    try {
        await apiWithRetry.clearPriceCache();
        await refreshAssetCacheStatus();
        message = { type: 'success', text: 'Successfully cleared price cache' };
        retryCount.clearPrice = 0; // Reset retry count on success
    } catch (error: any) {
        console.error('Failed to clear price cache:', error);
        
        // Enhanced error handling with detailed information
        const errorMessage = error.message || 'Failed to clear price cache';
        const errorDetails = error.originalMessage || error.statusText || '';
        
        message = { 
            type: 'error', 
            text: errorMessage,
            details: errorDetails
        };
    } finally {
        isClearingPriceCache = false;
        clearMessageAfterDelay();
    }
}

async function handleClearConversionCache() {
    if (isClearingConversionCache) return;
    
    isClearingConversionCache = true;
    message = null;
    
    try {
        await apiWithRetry.clearConversionCache();
        await refreshAssetCacheStatus();
        message = { type: 'success', text: 'Successfully cleared conversion cache' };
        retryCount.clearConversion = 0; // Reset retry count on success
    } catch (error: any) {
        console.error('Failed to clear conversion cache:', error);
        
        // Enhanced error handling with detailed information
        const errorMessage = error.message || 'Failed to clear conversion cache';
        const errorDetails = error.originalMessage || error.statusText || '';
        
        message = { 
            type: 'error', 
            text: errorMessage,
            details: errorDetails
        };
    } finally {
        isClearingConversionCache = false;
        clearMessageAfterDelay();
    }
}

// Use a single timer reference for message clearing
let messageTimer: ReturnType<typeof setTimeout> | null = null;
function clearMessageAfterDelay() {
    if (messageTimer) {
        clearTimeout(messageTimer);
    }
    
    messageTimer = setTimeout(() => {
        message = null;
        messageTimer = null;
    }, 5000);
}

// Retry functions with exponential backoff
async function retryRefreshAll() {
    if (retryCount.refresh >= maxRetries) {
        message = { 
            type: 'error', 
            text: `Failed after ${maxRetries} retry attempts`,
            details: 'Maximum retry attempts reached. Please try again later.'
        };
        return;
    }
    
    retryCount.refresh++;
    await handleRefreshAll();
}

async function retryClearPriceCache() {
    if (retryCount.clearPrice >= maxRetries) {
        message = { 
            type: 'error', 
            text: `Failed after ${maxRetries} retry attempts`,
            details: 'Maximum retry attempts reached. Please try again later.'
        };
        return;
    }
    
    retryCount.clearPrice++;
    await handleClearPriceCache();
}

async function retryClearConversionCache() {
    if (retryCount.clearConversion >= maxRetries) {
        message = { 
            type: 'error', 
            text: `Failed after ${maxRetries} retry attempts`,
            details: 'Maximum retry attempts reached. Please try again later.'
        };
        return;
    }
    
    retryCount.clearConversion++;
    await handleClearConversionCache();
}

onMount(() => {
    // Note: Cache status is automatically managed by CacheStatusProvider
    // No need to refresh here
    
    // Clean up timers on component destruction
    return () => {
        if (refreshTimeout) clearTimeout(refreshTimeout);
        if (messageTimer) clearTimeout(messageTimer);
    };
});
</script>

<div class="cache-manager bg-surface rounded-lg p-4 shadow-md">
    <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">Cache Management</h2>
        
        {#if !compact}
            <CacheHealthIndicator />
        {/if}
    </div>
    
    {#if message}
        {#if message.type === 'success'}
            <div class="mb-4 p-2 rounded text-sm bg-green-100 text-green-800">
                {message.text}
            </div>
        {:else if message.type === 'error'}
            <ErrorState 
                message={message.text}
                details={message.details}
                severity="error"
                inline={false}
                onRetry={retryHandler}
            />
        {/if}
    {/if}
    
    <div class="flex flex-wrap gap-2 mb-4">
        <button 
            class="bg-primary text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            on:click={handleRefreshAll}
            disabled={isRefreshing}
        >
            {#if isRefreshing}
                <LoadingIndicator size="small" inline={true} />
                <span>Refreshing...</span>
            {:else}
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
                <span>Refresh All</span>
            {/if}
        </button>
        
        <button 
            class="bg-red-500 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            on:click={handleClearPriceCache}
            disabled={isClearingPriceCache}
        >
            {#if isClearingPriceCache}
                <LoadingIndicator size="small" inline={true} color="light" />
                <span>Clearing...</span>
            {:else}
                <span>Clear Price Cache</span>
            {/if}
        </button>
        
        <button 
            class="bg-red-500 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            on:click={handleClearConversionCache}
            disabled={isClearingConversionCache}
        >
            {#if isClearingConversionCache}
                <LoadingIndicator size="small" inline={true} color="light" />
                <span>Clearing...</span>
            {:else}
                <span>Clear Conversion Cache</span>
            {/if}
        </button>
    </div>
    
    {#if !compact}
        <TransitionWrapper isLoading={!$priceCacheStats || !$conversionCacheStats} transitionType="fade">
            <svelte:fragment slot="loading">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <CardSkeleton height="8rem" contentLines={3} hasFooter={false} />
                    <CardSkeleton height="8rem" contentLines={3} hasFooter={false} />
                </div>
            </svelte:fragment>
            
            {#if $priceCacheStats && $conversionCacheStats}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-background rounded p-3">
                        <h3 class="text-sm font-medium mb-2">Price Cache</h3>
                        <div class="text-xs space-y-1">
                            <div>Total entries: {$priceCacheStats.total_entries}</div>
                            <div>Fresh entries: {$priceCacheStats.fresh_entries}</div>
                            <div>Cache age: {$priceCacheStats.cache_age_minutes} minutes</div>
                        </div>
                    </div>
                    
                    <div class="bg-background rounded p-3">
                        <h3 class="text-sm font-medium mb-2">Conversion Cache</h3>
                        <div class="text-xs space-y-1">
                            <div>Total entries: {$conversionCacheStats.total_entries}</div>
                            <div>Fresh entries: {$conversionCacheStats.fresh_entries}</div>
                            <div>Cache age: {$conversionCacheStats.cache_age_hours} hours</div>
                        </div>
                    </div>
                </div>
            {/if}
        </TransitionWrapper>
    {/if}
</div>