<script lang="ts">
/**
 * ListSkeleton component for displaying skeleton loaders for list items
 * 
 * This component provides a standardized way to show skeleton loading states
 * for list components with customizable structure.
 */

import SkeletonLoader from './SkeletonLoader.svelte';

export let items: number = 5;
export let hasIcon: boolean = true;
export let lineWidth: string = '100%';
export let itemHeight: string = '3rem';
export let animate: boolean = true;
</script>

<div class="list-skeleton">
    {#each Array(items) as _, i}
        <div class="list-item-skeleton" style="height: {itemHeight};">
            {#if hasIcon}
                <div class="list-item-icon">
                    <SkeletonLoader 
                        type="circle" 
                        width="2rem" 
                        height="2rem" 
                        {animate}
                    />
                </div>
            {/if}
            
            <div class="list-item-content">
                <SkeletonLoader 
                    type="rectangle" 
                    width={lineWidth} 
                    height="1rem" 
                    rounded={true} 
                    {animate}
                />
            </div>
        </div>
    {/each}
</div>

<style>
    .list-skeleton {
        display: flex;
        flex-direction: column;
        width: 100%;
    }

    .list-item-skeleton {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    .list-item-icon {
        margin-right: 1rem;
        flex-shrink: 0;
    }

    .list-item-content {
        flex: 1;
    }
</style>