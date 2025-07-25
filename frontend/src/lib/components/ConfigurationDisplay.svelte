<script lang="ts">
	import { getAllEnvironmentSettings } from '$lib/utils/environment';

	// Get all environment settings
	const settings = getAllEnvironmentSettings();

	// Format milliseconds to human-readable time
	function formatTime(ms: number): string {
		if (ms < 60000) {
			return `${ms / 1000} seconds`;
		} else if (ms < 3600000) {
			return `${ms / 60000} minutes`;
		} else {
			return `${ms / 3600000} hours`;
		}
	}
</script>

<div class="config-display">
	<h2 class="mb-4 text-xl font-bold">Current Configuration</h2>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<div class="bg-surface rounded-md p-4">
			<h3 class="mb-2 text-lg font-semibold">Cache Settings</h3>
			<ul class="space-y-2">
				<li>
					<span class="font-medium">Price Cache TTL:</span>
					<span class="ml-2">{formatTime(settings.priceCacheTTL.value)}</span>
					<div class="text-xs text-gray-400">Environment: {settings.priceCacheTTL.envVariable}</div>
				</li>
				<li>
					<span class="font-medium">Conversion Cache TTL:</span>
					<span class="ml-2">{formatTime(settings.conversionCacheTTL.value)}</span>
					<div class="text-xs text-gray-400">
						Environment: {settings.conversionCacheTTL.envVariable}
					</div>
				</li>
			</ul>
		</div>

		<div class="bg-surface rounded-md p-4">
			<h3 class="mb-2 text-lg font-semibold">Application Settings</h3>
			<ul class="space-y-2">
				<li>
					<span class="font-medium">Default Currency:</span>
					<span class="ml-2">{settings.defaultCurrency.value}</span>
					<div class="text-xs text-gray-400">
						Environment: {settings.defaultCurrency.envVariable}
					</div>
				</li>
				<li>
					<span class="font-medium">Force Refresh Only:</span>
					<span class="ml-2 {settings.forceRefreshOnly.value ? 'text-red-500' : 'text-green-500'}">
						{settings.forceRefreshOnly.displayValue}
					</span>
					<div class="text-xs text-gray-400">
						Environment: {settings.forceRefreshOnly.envVariable}
					</div>
				</li>
				<li>
					<span class="font-medium">API Base URL:</span>
					<span class="ml-2 text-sm">{settings.apiBaseUrl.value}</span>
					<div class="text-xs text-gray-400">Environment: {settings.apiBaseUrl.envVariable}</div>
				</li>
			</ul>
		</div>
	</div>
</div>

<style>
	.config-display {
		margin: 1rem 0;
	}
</style>
