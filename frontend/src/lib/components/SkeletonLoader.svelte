<script lang="ts">
/**
 * SkeletonLoader component for displaying content placeholders during loading
 * 
 * This component provides a standardized way to show skeleton loading states
 * for different types of content.
 */

export let type: 'text' | 'card' | 'table-cell' | 'circle' | 'rectangle' = 'text';
export let width: string = 'auto';
export let height: string = 'auto';
export let rounded: boolean = true;
export let animate: boolean = true;
export let count: number = 1;

// Get appropriate classes based on the type
function getTypeClasses(): string {
    switch (type) {
        case 'card':
            return 'h-32 w-full rounded-lg';
        case 'table-cell':
            return 'h-6 w-16 rounded';
        case 'circle':
            return 'rounded-full aspect-square';
        case 'rectangle':
            return rounded ? 'rounded' : '';
        case 'text':
        default:
            return 'h-4 rounded';
    }
}

$: typeClasses = getTypeClasses();
$: animateClass = animate ? 'animate-pulse' : '';
</script>

<div class="skeleton-container">
    {#each Array(count) as _, i}
        <div 
            class="skeleton {typeClasses} {animateClass}" 
            style="width: {width}; height: {height};"
            aria-hidden="true"
        ></div>
    {/each}
</div>

<style>
    .skeleton-container {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .skeleton {
        background-color: rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }

    .animate-pulse {
        animation: pulse 1.5s ease-in-out infinite;
    }

    .skeleton::after {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        transform: translateX(-100%);
        background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.1) 50%,
            rgba(255, 255, 255, 0) 100%
        );
        animation: shimmer 2s infinite;
    }

    @keyframes shimmer {
        100% {
            transform: translateX(100%);
        }
    }

    @keyframes pulse {
        0%, 100% {
            opacity: 0.5;
        }
        50% {
            opacity: 0.8;
        }
    }
</style>