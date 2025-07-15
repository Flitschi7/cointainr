<script lang="ts">
import { onMount } from 'svelte';
import { browser } from '$app/environment';
import { getStockPrice, getCryptoPrice, convertCurrency } from '$lib/services/api';
import type { PriceResponse } from '$lib/services/api';

export let symbol: string;
export let quantity: number;
export let purchasePrice: number | null;
export let currency: string;
export let assetType: 'stock' | 'crypto';
export let refreshTrigger: number = 0;
export let displayType: 'percentage' | 'absolute' = 'percentage';

let currentPrice: number | null = null;
let profitLoss: number | null = null;
let profitLossPercentage: number | null = null;
let isLoading = true;
let error: string | null = null;

onMount(async () => {
    if (browser && purchasePrice) {
        await fetchPriceAndCalculate();
    }
});

// Watch for refresh trigger changes
let lastRefreshTrigger = 0;
$: if (browser && refreshTrigger > lastRefreshTrigger && purchasePrice) {
    fetchPriceAndCalculate();
    lastRefreshTrigger = refreshTrigger;
}

async function fetchPriceAndCalculate() {
    if (!purchasePrice) {
        isLoading = false;
        return;
    }

    try {
        isLoading = true;
        error = null;
        
        let priceData: PriceResponse;
        
        if (assetType === 'stock') {
            priceData = await getStockPrice(symbol, false);
        } else {
            priceData = await getCryptoPrice(symbol, false);
        }
        
        if (priceData.price !== undefined) {
            currentPrice = priceData.price;
            
            // Convert current price to purchase currency if needed
            let convertedCurrentPrice = currentPrice;
            if (priceData.currency && priceData.currency !== currency) {
                try {
                    const conversionData = await convertCurrency(priceData.currency, currency, currentPrice);
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
        } else {
            error = 'Failed to get price';
        }
    } catch (e) {
        error = 'Error calculating profit/loss';
        console.error('Error calculating profit/loss:', e);
    } finally {
        isLoading = false;
    }
}

function formatValue(value: number | null): string {
    if (value === null) return '-';
    
    if (displayType === 'percentage') {
        const sign = value >= 0 ? '+' : '';
        return `${sign}${value.toFixed(2)}%`;
    } else {
        const sign = value >= 0 ? '+' : '';
        return `${sign}${Math.abs(value).toFixed(2)} ${currency}`;
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
    <span class="text-loss text-sm">Error</span>
{:else}
    <span class={getColorClass(displayValue)}>
        {formatValue(displayValue)}
    </span>
{/if}
