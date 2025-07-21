# Loading Components

This directory contains a set of components for handling loading states in the application. These components provide a consistent way to show loading states, skeleton loaders, and transitions between loading and loaded states.

## Components

### LoadingIndicator.svelte

A simple loading spinner component with configurable size, color, and text.

**Props:**

- `size`: 'small' | 'medium' | 'large' (default: 'medium')
- `inline`: boolean (default: false) - Whether to display inline or as a block
- `text`: string | null (default: null) - Optional text to display with the spinner
- `color`: 'primary' | 'secondary' | 'light' | 'dark' (default: 'primary')

**Example:**

```svelte
<LoadingIndicator size="small" inline={true} text="Loading..." />
```

### SkeletonLoader.svelte

A component for displaying skeleton loading placeholders for different types of content.

**Props:**

- `type`: 'text' | 'card' | 'table-cell' | 'circle' | 'rectangle' (default: 'text')
- `width`: string (default: 'auto')
- `height`: string (default: 'auto')
- `rounded`: boolean (default: true)
- `animate`: boolean (default: true)
- `count`: number (default: 1) - Number of skeleton items to display

**Example:**

```svelte
<SkeletonLoader type="text" width="80%" count={3} />
```

### TransitionWrapper.svelte

A component for smoothly transitioning between loading and loaded states.

**Props:**

- `isLoading`: boolean (default: false)
- `loadingDelay`: number (default: 200) - Delay before showing loading state
- `transitionDuration`: number (default: 200) - Duration of the transition animation
- `transitionType`: 'fade' | 'fly' | 'slide' (default: 'fade')
- `showLoadingImmediately`: boolean (default: false) - Whether to show loading state immediately without delay

**Example:**

```svelte
<TransitionWrapper {isLoading} transitionType="fade">
	<svelte:fragment slot="loading">
		<SkeletonLoader type="text" width="100%" count={3} />
	</svelte:fragment>

	<div>Loaded content goes here</div>
</TransitionWrapper>
```

### TableCellSkeleton.svelte

A specialized skeleton loader for table cells.

**Props:**

- `width`: string (default: '100%')
- `height`: string (default: '1.5rem')
- `animate`: boolean (default: true)

**Example:**

```svelte
<TableCellSkeleton width="4rem" />
```

### CardSkeleton.svelte

A skeleton loader for card-like elements with customizable content structure.

**Props:**

- `width`: string (default: '100%')
- `height`: string (default: 'auto')
- `hasHeader`: boolean (default: true)
- `contentLines`: number (default: 3)
- `hasFooter`: boolean (default: true)
- `animate`: boolean (default: true)
- `rounded`: boolean (default: true)

**Example:**

```svelte
<CardSkeleton contentLines={5} hasFooter={false} />
```

### ListSkeleton.svelte

A skeleton loader for list items.

**Props:**

- `items`: number (default: 5)
- `hasIcon`: boolean (default: true)
- `lineWidth`: string (default: '100%')
- `itemHeight`: string (default: '3rem')
- `animate`: boolean (default: true)

**Example:**

```svelte
<ListSkeleton items={10} hasIcon={false} />
```

### TableSkeleton.svelte

A skeleton loader for tables with customizable structure.

**Props:**

- `rows`: number (default: 5)
- `columns`: number (default: 4)
- `hasHeader`: boolean (default: true)
- `cellHeight`: string (default: '2.5rem')
- `animate`: boolean (default: true)
- `columnWidths`: string[] (default: []) - Custom widths for each column

**Example:**

```svelte
<TableSkeleton rows={10} columns={5} columnWidths={['30%', '20%', '20%', '20%', '10%']} />
```

### PageLoader.svelte

A component for displaying loading states at the page level.

**Props:**

- `text`: string (default: 'Loading...')
- `fullPage`: boolean (default: false) - Whether to display as a full-page overlay

**Example:**

```svelte
<PageLoader text="Loading data..." fullPage={true} />
```

## Utilities

### loadingState.ts

Utility functions for managing loading states.

**Functions:**

- `createLoadingState(initialState: boolean = false)`: Creates a loading state store with helper methods
- `createMultiLoadingState()`: Creates a loading state store for multiple operations
- `debounceLoadingState(isLoading: boolean, delay: number = 200)`: Debounces a loading state to prevent flickering

**Example:**

```typescript
import { createLoadingState } from '$lib/utils/loadingState';

const loading = createLoadingState();

// Use the loading state in a component
$: isLoading = $loading;

// Wrap an async function with loading state management
const fetchData = loading.withLoading(async () => {
	const response = await fetch('/api/data');
	return response.json();
});
```
