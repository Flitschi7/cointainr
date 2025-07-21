<script lang="ts">
import { onMount } from 'svelte';
import { browser } from '$app/environment';
import type { PriceResponse, ConversionResponse } from '$lib/types';
import { formatCurrency } from '$lib/utils/numberFormat';
import CacheIndicator from './CacheIndicator.svelte';
import ErrorState from './ErrorState.svelte';
import TransitionWrapper from './TransitionWrapper.svelte';
import TableCellSkeleton from './TableCellSkeleton.svelte';
import * as enhancedApi from '$lib/services/enhancedApi';
import * as apiWithRetry from '$lib/services/apiWithRetry';
import { withRetry } from '$lib/utils/retryUtils';

export let symbol: string;
export let quantity: number;
export let currency: string;
export let assetType: 'stock' | 'crypto' = 'stock'; // New prop to distinguish asset types
export let refreshTrigger: number = 0; // Change to numeric trigger instead of boolean
export let showCacheStatus: boolean = false; // Whether to show cache status indicator

let value: number | null = null;
let error: string | null = null;
let errorDetails: string | null = null;
let isLoading = true;
let priceData: PriceResponse | null = null;
let isCached: boolean = false; // Track if the current data is from cache
let isStale: boolean = false; // Track if the data is stale
let retryCount = 0;
let maxRetries = 3;

// Memoized values to prevent unnecessary calculations
let formattedValue: string = '-';
let cacheStatusProps = { isCached: false, lastUpdated: null, isStale: false };

// Memoize the formatted value calculation
$: if (value !== null) {
    formattedValue = formatCurrency(value, currency);
} else {
    formattedValue = '-';
}

// Memoize cache status props to prevent unnecessary object creation
$: cacheStatusProps = {
    isCached,
    lastUpdated: priceData?.fetched_at || null,
    isStale
};

onMount(async () => {
    if (browser) {
        // Use cache-first approach when component mounts
        await fetchPrice(false);
    }
});

// Watch for refresh trigger changes - use memoization to prevent unnecessary fetches
$: if (browser && refreshTrigger > 0 && refreshTrigger !== lastRefreshTrigger) {
    fetchPrice(true); // Force refresh when triggered manually
}

// Track the last refresh trigger to avoid duplicate fetches
let lastRefreshTrigger = 0;
$: if (refreshTrigger > lastRefreshTrigger) {
    lastRefreshTrigger = refreshTrigger;
}

// Optimize by creating a memoized function that only runs when inputs change
async function fetchPrice(shouldForceRefresh: boolean = false) {
    // Skip fetch if symbol is empty
    if (!symbol) {
        error = 'No symbol provided';
        isLoading = false;
        return;
    }
    
    // Reset error state but keep previous value during loading for better UX
    const previousValue = value;
    error = null;
    errorDetails = null;
    isLoading = true;
    
    try {
        // Fallbacks for empty props
        const safeSymbol = symbol;
        const safeCurrency = currency || 'USD';

        // Use the API with retry logic
        priceData = await apiWithRetry.getPrice(safeSymbol, assetType, { 
            forceRefresh: shouldForceRefresh 
        });

        if (!priceData || !priceData.price) {
            error = 'No price available for symbol';
            isLoading = false;
            return;
        }

        // Track if the data is from cache
        isCached = priceData.cached === true;
        
        // Get cache status information - only when needed
        const cacheInfo = enhancedApi.getAssetCacheInfo(safeSymbol, assetType);
        isStale = !cacheInfo.isValid && cacheInfo.isCached;

        let price = priceData.price;
        let priceCurrency = priceData.currency || 'USD';

        // Convert to selected currency if needed using cache-first approach with retry
        if (safeCurrency && safeCurrency !== priceCurrency) {
            const conversionData = await apiWithRetry.convertCurrency(
                priceCurrency, 
                safeCurrency, 
                price, 
                { forceRefresh: shouldForceRefresh }
            );
            price = conversionData.converted;
        }

        value = price * quantity;
        retryCount = 0; // Reset retry count on success
    } catch (e: any) {
        handleError(e, previousValue, symbol);
    } finally {
        isLoading = false;
    }
}

function handleError(e: any, previousValue: number | null, symbol: string): void {
    // If we have a previous value, keep it and just show a warning
    if (previousValue !== null) {
        value = previousValue;
        isCached = true; // Mark as cached since we're using previous value
        isStale = true;  // Mark as stale since we couldn't refresh
        
        // Provide more detailed error information
        const errorMessage = e.message || 'Unknown error';
        const originalMessage = e.originalMessage || errorMessage;
        
        // Determine error type for better user feedback
        let errorSource = 'API error';
        
        if (e.isNetworkError || (originalMessage && originalMessage.includes('network'))) {
            errorSource = 'Network error';
        } else if (originalMessage && originalMessage.includes('timeout')) {
            errorSource = 'API timeout';
        } else if (e.category === 'rate-limit') {
            errorSource = 'Rate limit exceeded';
        } else if (e.status === 404) {
            errorSource = 'Resource not found';
        }
        
        console.warn(`Using cached value for ${symbol} due to ${errorSource}:`, e);
        
        // Set a non-blocking error that won't prevent display but will show in tooltip
        error = `Using cached data. ${errorSource}`;
        errorDetails = originalMessage;
    } else {
        // No previous value to fall back to
        error = e.message || 'Failed to fetch price data';
        errorDetails = e.originalMessage || 'Unable to retrieve price information';
        console.error('Error fetching price:', e);
    }
}

// Function to retry fetching with exponential backoff
async function retryFetch() {
    if (retryCount >= maxRetries) {
        error = `Failed after ${maxRetries} retry attempts`;
        return;
    }
    
    retryCount++;
    await fetchPrice(true);
}
</script>

<span class="value-cell">
    <TransitionWrapper isLoading={isLoading} transitionType="fade" transitionDuration={150}>
        <svelte:fragment slot="loading">
            <TableCellSkeleton width="4rem" />
        </svelte:fragment>
        
        {#if error && value === null}
            <ErrorState 
                message="Error" 
                details={errorDetails || error} 
                severity="error" 
                inline={true} 
                onRetry={retryFetch} 
            />
        {:else if error && value !== null}
            <span class="value-display">
                {formatCurrency(value, currency)}
                <ErrorState 
                    message="!" 
                    details={error} 
                    severity="warning" 
                    inline={true} 
                    showIcon={false} 
                    onRetry={retryFetch} 
                />
                {#if showCacheStatus}
                    <span class="ml-1">
                        <CacheIndicator 
                            isCached={isCached} 
                            lastUpdated={priceData?.fetched_at || null}
                            isStale={isStale}
                        />
                    </span>
                {/if}
            </span>
        {:else if value !== null}
            <span class="value-display">
                {formatCurrency(value, currency)}
                {#if showCacheStatus}
                    <span class="ml-1">
                        <CacheIndicator 
                            isCached={isCached} 
                            lastUpdated={priceData?.fetched_at || null}
                            isStale={isStale}
                        />
                    </span>
                {/if}
            </span>
        {:else}
            -
        {/if}
    </TransitionWrapper>
</span>

<style>
    .value-cell {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .value-display {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    

    
    .ml-1 {
        margin-left: 0.25rem;
    }
</style>
