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

let value: number | null = null;
let error: string | null = null;
let isLoading = true;
let priceData: PriceResponse | null = null;

onMount(async () => {
    if (browser) {
        await fetchPrice(false); // Use cache on initial load
    }
});

// Watch for refresh trigger changes - fetch cached prices after refresh
let lastRefreshTrigger = 0;
$: if (browser && refreshTrigger > lastRefreshTrigger) {
    fetchPrice(false); // Use cache since refresh-all already updated prices
    lastRefreshTrigger = refreshTrigger;
}

async function fetchPrice(shouldForceRefresh: boolean = false) {
    // Reset state
    value = null;
    error = null;
    isLoading = true;
    priceData = null;
    
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

        if (!priceData.price) {
            error = 'No price available for symbol';
            return;
        }

        let price = priceData.price;
        let priceCurrency = priceData.currency || 'USD';

        // Convert to selected currency if needed (force refresh only when explicitly requested)
        if (safeCurrency && safeCurrency !== priceCurrency) {
            const conversionData = await convertCurrency(priceCurrency, safeCurrency, price, shouldForceRefresh);
            price = conversionData.converted;
        }

        value = price * quantity;
    } catch (e: any) {
        error = e.message;
        console.error('Error fetching price:', e);
    } finally {
        isLoading = false;
    }
}
</script>

<span>
    {#if isLoading}
        <span class="text-gray-400">...</span>
    {:else if error}
        <span class="text-loss" title={error}>Error</span>
    {:else if value !== null}
        {formatCurrency(value, currency)}
    {:else}
        -
    {/if}
</span>
