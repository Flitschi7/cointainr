<script lang="ts">
/**
 * LoadingIndicator component for displaying loading states
 * 
 * This component provides a standardized way to show loading states in the application
 * with different sizes and styles.
 */

export let size: 'small' | 'medium' | 'large' = 'medium';
export let inline: boolean = false;
export let text: string | null = null;
export let color: string = 'primary'; // primary, secondary, light, dark

// Get size classes based on the size prop
function getSizeClasses(): string {
    switch (size) {
        case 'small':
            return 'w-4 h-4';
        case 'large':
            return 'w-8 h-8';
        case 'medium':
        default:
            return 'w-6 h-6';
    }
}

// Get color classes based on the color prop
function getColorClasses(): string {
    switch (color) {
        case 'secondary':
            return 'text-gray-400';
        case 'light':
            return 'text-gray-200';
        case 'dark':
            return 'text-gray-600';
        case 'primary':
        default:
            return 'text-primary';
    }
}

$: sizeClasses = getSizeClasses();
$: colorClasses = getColorClasses();
</script>

<div class="loading-indicator {inline ? 'inline' : ''}" aria-live="polite" aria-busy="true">
    <div class="spinner {sizeClasses} {colorClasses}">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <circle class="spinner-track" cx="12" cy="12" r="10" stroke-width="4" fill="none" />
            <circle class="spinner-head" cx="12" cy="12" r="10" stroke-width="4" stroke-dasharray="62.83" stroke-dashoffset="62.83" fill="none" />
        </svg>
    </div>
    {#if text}
        <span class="loading-text">{text}</span>
    {/if}
</div>

<style>
    .loading-indicator {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }

    .loading-indicator.inline {
        display: inline-flex;
        flex-direction: row;
    }

    .spinner {
        position: relative;
        animation: rotate 1.5s linear infinite;
    }

    .spinner-track {
        stroke: currentColor;
        opacity: 0.2;
    }

    .spinner-head {
        stroke: currentColor;
        stroke-linecap: round;
        animation: dash 1.5s ease-in-out infinite;
    }

    .loading-text {
        font-size: 0.875rem;
        color: inherit;
        opacity: 0.8;
    }

    @keyframes rotate {
        100% {
            transform: rotate(360deg);
        }
    }

    @keyframes dash {
        0% {
            stroke-dashoffset: 62.83;
        }
        50% {
            stroke-dashoffset: 15.71;
        }
        100% {
            stroke-dashoffset: 62.83;
        }
    }

    .text-primary {
        color: #00C896; /* Primary color from design system */
    }
</style>