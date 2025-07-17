<script lang="ts">
import { onMount } from 'svelte';
import { browser } from '$app/environment';
import { getStockPrice, getCryptoPrice, convertCurrency } from '$lib/services/api';
import type { PriceResponse } from '$lib/services/api';
import { formatCurrency } from '$lib/utils/numberFormat';

export let symbol: string;
export let quantity: number;
export let currency: string;
export let assetType: 'stock' | 'crypto' = 'stock'; // New prop to distinguish asset types
export let refreshTrigger: number = 0; // Change to numeric trigger instead of boolean
export let showCacheStatus: boolean = false; // Whether to show cache status indicator

let value: number | null = null;
let error: string | null = null;
let isLoading = true;
let priceData: PriceResponse | null = null;
let isCached: boolean = false; // Track if the current data is from cache

onMount(async () => {
    if (browser) {
        // Check if we already have data from the page load
        // If not, fetch with cache respect (false = don't force refresh)
        await fetchPrice(false);
    }
});

// Watch for refresh trigger changes
let lastRefreshTrigger = 0;
$: if (browser && refreshTrigger > lastRefreshTrigger) {
    // When refresh trigger is incremented, it means a manual refresh was triggered
    // In this case, we should use the cached data that was just refreshed by the refresh-all endpoint
    // We don't need to force refresh here because the cache was already updated
    fetchPrice(false);
    lastRefreshTrigger = refreshTrigger;
}

async function fetchPrice(shouldForceRefresh: boolean = false) {
    // Reset state but keep previous value during loading for better UX
    const previousValue = value;
    error = null;
    isLoading = true;
    
    try {
        // Fallbacks for empty props
        const safeSymbol = symbol || '';
        const safeCurrency = currency || 'USD';
        
        if (!safeSymbol) {
            error = 'No symbol provided';
            return;
        }

        // Fetch price based on asset type (force refresh only when explicitly requested)
        if (assetType === 'crypto') {
            priceData = await getCryptoPrice(safeSymbol, shouldForceRefresh);
        } else {
            priceData = await getStockPrice(safeSymbol, shouldForceRefresh);
        }

        if (!priceData || !priceData.price) {
            error = 'No price available for symbol';
            return;
        }

        // Track if the data is from cache
        isCached = priceData.cached === true;

        let price = priceData.price;
        let priceCurrency = priceData.currency || 'USD';

        // Convert to selected currency if needed (force refresh only when explicitly requested)
        if (safeCurrency && safeCurrency !== priceCurrency) {
            const conversionData = await convertCurrency(priceCurrency, safeCurrency, price, shouldForceRefresh);
            price = conversionData.converted;
        }

        value = price * quantity;
    } catch (e: any) {
        // If we have a previous value, keep it and just show a warning
        if (previousValue !== null) {
            value = previousValue;
            isCached = true; // Mark as cached since we're using previous value
            
            // Provide more detailed error information
            const errorMessage = e.message || 'Unknown error';
            const errorSource = errorMessage.includes('network') ? 'Network error' : 
                               errorMessage.includes('timeout') ? 'API timeout' : 
                               'API error';
            
            console.warn(`Using cached value for ${symbol} due to ${errorSource}:`, errorMessage);
            
            // Set a non-blocking error that won't prevent display but will show in tooltip
            error = `Using cached data. ${errorSource}: ${errorMessage}`;
        } else {
            // No previous value to fall back to
            error = e.message || 'Failed to fetch price data';
            console.error('Error fetching price:', e);
        }
    } finally {
        isLoading = false;
    }
}
</script>

<span class="value-cell">
    {#if isLoading}
        <span class="text-gray-400">...</span>
    {:else if error}
        <span class="text-loss" title={error}>Error</span>
    {:else if value !== null}
        <span class="value-display">
            {formatCurrency(value, currency)}
            {#if showCacheStatus}
                <span class="cache-indicator" class:cached={isCached} class:fresh={!isCached} title={isCached ? 'Using cached data' : 'Using fresh data'}>
                    {isCached ? '•' : '•'}
                </span>
            {/if}
        </span>
    {:else}
        -
    {/if}
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
    
    .cache-indicator {
        font-size: 1.2em;
        line-height: 1;
    }
    
    .cached {
        color: #f59e0b; /* Amber-500 */
    }
    
    .fresh {
        color: #10b981; /* Emerald-500 */
    }
</style>
