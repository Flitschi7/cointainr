<script lang="ts">
/**
 * CardSkeleton component for displaying skeleton loaders for card-like elements
 * 
 * This component provides a standardized way to show skeleton loading states
 * for card components with customizable content structure.
 */

import SkeletonLoader from './SkeletonLoader.svelte';

export let width: string = '100%';
export let height: string = 'auto';
export let hasHeader: boolean = true;
export let contentLines: number = 3;
export let hasFooter: boolean = true;
export let animate: boolean = true;
export let rounded: boolean = true;
</script>

<div class="card-skeleton" style="width: {width}; height: {height};">
    {#if hasHeader}
        <div class="card-skeleton-header">
            <SkeletonLoader 
                type="rectangle" 
                width="60%" 
                height="1.5rem" 
                {rounded} 
                {animate}
            />
        </div>
    {/if}
    
    <div class="card-skeleton-content">
        {#each Array(contentLines) as _, i}
            <SkeletonLoader 
                type="rectangle" 
                width={`${85 - i * 10}%`} 
                height="1rem" 
                {rounded} 
                {animate}
            />
        {/each}
    </div>
    
    {#if hasFooter}
        <div class="card-skeleton-footer">
            <SkeletonLoader 
                type="rectangle" 
                width="40%" 
                height="1.25rem" 
                {rounded} 
                {animate}
            />
        </div>
    {/if}
</div>

<style>
    .card-skeleton {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 1rem;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 0.5rem;
    }

    .card-skeleton-header {
        margin-bottom: 0.5rem;
    }

    .card-skeleton-content {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        flex: 1;
    }

    .card-skeleton-footer {
        margin-top: 0.5rem;
        display: flex;
        justify-content: flex-end;
    }
</style>