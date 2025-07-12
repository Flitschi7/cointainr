import type { Asset } from '$lib/types';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// This is our existing function
export async function getAssets(): Promise<Asset[]> {
	const response = await fetch(`${API_BASE_URL}/assets/`);
	if (!response.ok) {
		throw new Error('Failed to fetch assets');
	}
	const assets: Asset[] = await response.json();
	return assets;
}

// Add this new function
export async function createAsset(assetData: Omit<Asset, 'id'>): Promise<Asset> {
	const response = await fetch(`${API_BASE_URL}/assets/`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(assetData)
	});
	if (!response.ok) {
		throw new Error('Failed to create asset');
	}
	const newAsset: Asset = await response.json();
	return newAsset;
}
