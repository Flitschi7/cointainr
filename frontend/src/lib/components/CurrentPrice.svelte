<script lang="ts">
import { onMount } from 'svelte';

export let symbol: string;
let price: number | null = null;
let error: string | null = null;
let isLoading = true;

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

onMount(async () => {
    try {
        const res = await fetch(`${API_BASE_URL}/price/stock/${symbol}`);
        if (!res.ok) throw new Error('Failed to fetch price');
        const data = await res.json();
        price = data.price;
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
        <span class="text-loss">Err</span>
    {:else if price !== null}
        {price.toFixed(2)} USD
    {:else}
        -
    {/if}
</span>
