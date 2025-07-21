<script lang="ts">
/**
 * PageLoader component for displaying loading states at the page level
 * 
 * This component provides a standardized way to show loading states
 * for entire pages or large sections.
 */

import LoadingIndicator from './LoadingIndicator.svelte';

export let text: string = 'Loading...';
export let fullPage: boolean = false;
</script>

<div class="page-loader {fullPage ? 'full-page' : ''}">
    <div class="loader-content">
        <LoadingIndicator size="large" text={text} />
    </div>
</div>

<style>
    .page-loader {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        min-height: 10rem;
    }

    .full-page {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(30, 30, 47, 0.8); /* Using the background color from design system with opacity */
        z-index: 50;
    }

    .loader-content {
        text-align: center;
    }
</style>