import type { Asset } from '$lib/types';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// --- Asset API Service ---

/**
 * Fetch all assets from the backend API.
 */
export async function getAssets(): Promise<Asset[]> {
	const response = await fetch(`${API_BASE_URL}/assets/`);
	if (!response.ok) {
		throw new Error('Failed to fetch assets');
	}
	return await response.json();
}

/**
 * Create a new asset.
 */
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
	return await response.json();
}

/**
 * Delete an asset by ID.
 */
export async function deleteAsset(assetId: number): Promise<void> {
	const response = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error('Failed to delete asset');
	}
}

/**
 * Update an asset by ID.
 */
export async function updateAsset(
	assetId: number,
	assetData: Partial<Omit<Asset, 'id'>>
): Promise<Asset> {
	const response = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(assetData)
	});
	if (!response.ok) {
		throw new Error('Failed to update asset');
	}
	return await response.json();
}
