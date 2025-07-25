<script lang="ts">
	/**
	 * TableCellSkeleton component for displaying skeleton loaders in table cells
	 *
	 * This component provides a standardized way to show skeleton loading states
	 * specifically designed for table cells.
	 */

	import SkeletonLoader from './SkeletonLoader.svelte';

	export let width: string = '100%';
	export let height: string = '1.5rem';
	export let animate: boolean = true;
</script>

<div class="table-cell-skeleton">
	<SkeletonLoader type="table-cell" {width} {height} {animate} />
</div>

<style>
	.table-cell-skeleton {
		display: inline-block;
		min-width: 2rem;
	}
</style>
