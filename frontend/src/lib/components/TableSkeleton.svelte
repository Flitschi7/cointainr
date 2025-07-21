<script lang="ts">
/**
 * TableSkeleton component for displaying skeleton loaders for tables
 * 
 * This component provides a standardized way to show skeleton loading states
 * for table components with customizable structure.
 */

import SkeletonLoader from './SkeletonLoader.svelte';

export let rows: number = 5;
export let columns: number = 4;
export let hasHeader: boolean = true;
export let cellHeight: string = '2.5rem';
export let animate: boolean = true;
export let columnWidths: string[] = [];

// Generate default column widths if not provided
$: effectiveColumnWidths = columnWidths.length === columns 
    ? columnWidths 
    : Array(columns).fill(0).map((_, i) => {
        // First column is usually wider
        if (i === 0) return '30%';
        // Last column might be for actions
        if (i === columns - 1) return '10%';
        // Distribute remaining columns evenly
        return `${60 / (columns - 2)}%`;
    });
</script>

<div class="table-skeleton">
    {#if hasHeader}
        <div class="table-header">
            {#each effectiveColumnWidths as width, i}
                <div class="header-cell" style="width: {width};">
                    <SkeletonLoader 
                        type="rectangle" 
                        width="80%" 
                        height="1.25rem" 
                        rounded={true} 
                        {animate}
                    />
                </div>
            {/each}
        </div>
    {/if}
    
    <div class="table-body">
        {#each Array(rows) as _, rowIndex}
            <div class="table-row">
                {#each effectiveColumnWidths as width, colIndex}
                    <div class="table-cell" style="width: {width}; height: {cellHeight};">
                        <SkeletonLoader 
                            type="table-cell" 
                            width={colIndex === 0 ? '80%' : '60%'} 
                            height="1rem" 
                            {animate}
                        />
                    </div>
                {/each}
            </div>
        {/each}
    </div>
</div>

<style>
    .table-skeleton {
        width: 100%;
        border-collapse: collapse;
    }

    .table-header {
        display: flex;
        padding: 0.75rem 1rem;
        background-color: rgba(255, 255, 255, 0.05);
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }

    .header-cell {
        display: flex;
        align-items: center;
    }

    .table-body {
        display: flex;
        flex-direction: column;
    }

    .table-row {
        display: flex;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    .table-cell {
        display: flex;
        align-items: center;
        padding: 0.5rem 1rem;
    }
</style>