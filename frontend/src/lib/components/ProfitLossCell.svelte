<script lang="ts">
import { onMount } from 'svelte';
import { browser } from '$app/environment';
import { getStockPrice, getCryptoPrice, convertCurrency } from '$lib/services/api';
import type { PriceResponse } from '$lib/services/api';
import { formatPercentage, formatCurrency } from '$lib/utils/numberFormat';

export let symbol: string;
export let quantity: number;
export let purchasePrice: number | null;
export let currency: string;
export let assetType: 'stock' | 'crypto';
export let refreshTrigger: number = 0;
export let displayType: 'percentage' | 'absolute' = 'percentage';
export let showCacheStatus: boolean = false; // Whether to show cache status indicator

let currentPrice: number | null = null;
let profitLoss: number | null = null;
let profitLossPercentage: number | null = null;
let isLoading = true;
let error: string | null = null;
let isCached: boolean = false; // Track if the current data is from cache

onMount(async () => {
    if (browser && purchasePrice) {
        // Use cached data for initial load (forceRefresh = false)
        await fetchPriceAndCalculate(false);
    }
});

// Watch for refresh trigger changes
let lastRefreshTrigger = 0;
$: if (browser && refreshTrigger > lastRefreshTrigger && purchasePrice) {
    // When refresh trigger is incremented, it means a manual refresh was triggered
    // In this case, we should use the cached data that was just refreshed by the refresh-all endpoint
    // We don't need to force refresh here because the cache was already updated
    fetchPriceAndCalculate(false);
    lastRefreshTrigger = refreshTrigger;
}

async function fetchPriceAndCalculate(shouldForceRefresh: boolean = false) {
    if (!purchasePrice) {
        isLoading = false;
        return;
    }

    // Store previous values for fallback in case of errors
    const previousProfitLoss = profitLoss;
    const previousProfitLossPercentage = profitLossPercentage;

    try {
        isLoading = true;
        error = null;
        
        let priceData: PriceResponse;
        
        // Respect cache by default, only force refresh when explicitly requested
        if (assetType === 'stock') {
            priceData = await getStockPrice(symbol, shouldForceRefresh);
        } else {
            priceData = await getCryptoPrice(symbol, shouldForceRefresh);
        }
        
        // Check if we got valid price data
        if (priceData && priceData.price !== undefined) {
            currentPrice = priceData.price;
            
            // Convert current price to purchase currency if needed
            let convertedCurrentPrice = currentPrice;
            if (priceData.currency && priceData.currency !== currency) {
                try {
                    // Respect cache for currency conversion too
                    const conversionData = await convertCurrency(priceData.currency, currency, currentPrice, shouldForceRefresh);
                    if (conversionData.converted !== undefined) {
                        convertedCurrentPrice = conversionData.converted;
                    }
                } catch (convError) {
                    console.warn('Currency conversion failed, using original price:', convError);
                }
            }
            
            // Calculate profit/loss
            const totalCurrentValue = convertedCurrentPrice * quantity;
            const totalPurchaseValue = purchasePrice * quantity;
            
            profitLoss = totalCurrentValue - totalPurchaseValue;
            profitLossPercentage = ((convertedCurrentPrice - purchasePrice) / purchasePrice) * 100;
            
            // Add cache status information to the component
            isCached = priceData.cached === true;
            console.debug(`${symbol} profit/loss calculation: ${isCached ? 'Using cached data' : 'Using fresh data'}`);
        } else {
            error = 'Failed to get price';
        }
    } catch (e: any) {
        // If we have previous values, keep them and just show a warning
        if (previousProfitLoss !== null && previousProfitLossPercentage !== null) {
            profitLoss = previousProfitLoss;
            profitLossPercentage = previousProfitLossPercentage;
            isCached = true; // Mark as cached since we're using previous value
            
            // Provide more detailed error information
            const errorMessage = e.message || 'Unknown error';
            const errorSource = errorMessage.includes('network') ? 'Network error' : 
                               errorMessage.includes('timeout') ? 'API timeout' : 
                               'API error';
            
            console.warn(`Using cached profit/loss values for ${symbol} due to ${errorSource}:`, errorMessage);
            
            // Set a non-blocking error that won't prevent display but will show in tooltip
            error = `Using cached data. ${errorSource}: ${errorMessage}`;
        } else {
            // No previous value to fall back to
            error = 'Error calculating profit/loss';
            console.error('Error calculating profit/loss:', e);
        }
    } finally {
        isLoading = false;
    }
}

function formatValue(value: number | null): string {
    if (value === null) return '-';
    
    if (displayType === 'percentage') {
        return formatPercentage(value);
    } else {
        return formatCurrency(value, currency);
    }
}

function getColorClass(value: number | null): string {
    if (value === null) return '';
    if (value > 0) return 'text-profit';
    if (value < 0) return 'text-loss';
    return '';
}

$: displayValue = displayType === 'percentage' ? profitLossPercentage : profitLoss;
</script>

{#if !purchasePrice}
    <span class="text-gray-400">-</span>
{:else if isLoading}
    <span class="text-gray-400">...</span>
{:else if error}
    <span class="text-loss text-sm" title={error}>Error</span>
{:else}
    <span class="profit-loss-cell">
        <span class={getColorClass(displayValue)}>
            {formatValue(displayValue)}
        </span>
        {#if showCacheStatus}
            <span class="cache-indicator" class:cached={isCached} class:fresh={!isCached} title={isCached ? 'Using cached data' : 'Using fresh data'}>
                {isCached ? '•' : '•'}
            </span>
        {/if}
    </span>
{/if}

<style>
    .profit-loss-cell {
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
