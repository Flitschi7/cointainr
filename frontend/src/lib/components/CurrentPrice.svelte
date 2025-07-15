<script lang="ts">
import { onMount } from 'svelte';
import { browser } from '$app/environment';
import { getStockPrice, getCryptoPrice } from '$lib/services/api';
import type { PriceResponse } from '$lib/services/api';

export let symbol: string;
export let assetType: 'stock' | 'crypto' = 'stock';
export let forceRefresh: boolean = false;

let priceData: PriceResponse | null = null;
let error: string | null = null;
let isLoading = true;

onMount(async () => {
    if (browser) {
        await fetchPrice();
    }
});

// Watch for changes and refetch
$: if (browser && (symbol || forceRefresh)) {
    fetchPrice();
}

async function fetchPrice() {
    priceData = null;
    error = null;
    isLoading = true;
    
    try {
        if (!symbol) {
            error = 'No symbol provided';
            return;
        }

        if (assetType === 'crypto') {
            priceData = await getCryptoPrice(symbol, forceRefresh);
        } else {
            priceData = await getStockPrice(symbol, forceRefresh);
        }
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
        <span class="text-loss" title={error}>Err</span>
    {:else if priceData && priceData.price !== null}
        {priceData.price.toFixed(2)} {priceData.currency}
    {:else}
        -
    {/if}
</span>
