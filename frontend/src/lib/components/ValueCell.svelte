<script lang="ts">
import { onMount } from 'svelte';
export let symbol: string;
export let quantity: number;
export let currency: string;
let value: number | null = null;
let error: string | null = null;
let isLoading = true;

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

onMount(async () => {
    // Fallbacks for empty props
    const safeSymbol = symbol || '';
    const safeCurrency = currency || 'USD';
    try {
        // Get current price in USD
        if (!safeSymbol) {
            error = 'No symbol provided';
            return;
        }
        const res = await fetch(`${API_BASE_URL}/price/stock/${safeSymbol}`);
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            error = errData.detail || 'Failed to fetch price';
            return;
        }
        const data = await res.json();
        if (!data.price) {
            error = 'No price available for symbol';
            return;
        }
        let price = data.price;
        let priceCurrency = data.currency || 'USD';
        // Convert to selected currency if needed
        if (safeCurrency && safeCurrency !== priceCurrency) {
            const amount = typeof price === 'number' && !isNaN(price) ? price : 0;
            // Use correct query parameter names for backend
            const convRes = await fetch(`${API_BASE_URL}/price/convert?from_currency=${priceCurrency}&to_currency=${safeCurrency}&amount=${amount}`);
            if (!convRes.ok) {
                const convErrData = await convRes.json().catch(() => ({}));
                error = convErrData.detail || 'Failed to convert price';
                return;
            }
            const convData = await convRes.json();
            // For exchangerate-api.com, the result is in conversion_result
            if (typeof convData.conversion_result === 'number') {
                price = convData.conversion_result;
            } else if (typeof convData.converted === 'number') {
                price = convData.converted;
            } else {
                error = 'Conversion failed';
                return;
            }
        }
        value = price * quantity;
    } catch (e: any) {
        error = e.message;
    } finally {
        isLoading = false;
    }
});
</script>

<span>
    {#if isLoading}
        ...
    {:else if error}
        <span class="text-loss">{typeof error === 'string' ? error : 'Error'}</span>
    {:else if value !== null}
        {value.toFixed(2)} {currency}
    {:else}
        -
    {/if}
</span>
