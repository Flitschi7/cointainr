import type { Asset, PriceResponse } from '$lib/types';
import { devLog } from '$lib/utils/logger';
import * as enhancedApi from './enhancedApi';

export class PriceManagementService {
	private assetPrices: Map<number, { price: number; currency: string }> = new Map();
	private pricesLoaded = false;

	async fetchAllCurrentPrices(
		assets: Asset[],
		forceRefresh: boolean = false
	): Promise<Map<number, { price: number; currency: string }>> {
		console.log(`=== fetchAllCurrentPrices START (forceRefresh: ${forceRefresh}) ===`);
		console.log('allAssets:', assets);
		console.log(
			'Non-cash assets to fetch prices for:',
			assets.filter((asset) => asset.type !== 'cash')
		);

		try {
			const pricePromises = assets
				.filter((asset) => asset.type !== 'cash') // Skip cash assets
				.map(async (asset) => {
					console.log(
						`Fetching price for asset: ${asset.symbol}, type: ${asset.type}, forceRefresh: ${forceRefresh}`
					);
					try {
						// Use the enhanced API with cache-first approach
						const priceData = await enhancedApi.getPrice(
							asset.symbol || '',
							asset.type as 'stock' | 'crypto',
							{
								forceRefresh
							}
						);

						console.log(`Price data for ${asset.symbol}:`, priceData);

						if (priceData) {
							return {
								assetId: asset.id,
								price: priceData.price || 0,
								currency: priceData.currency || 'USD'
							};
						}
					} catch (error) {
						console.error(`Failed to fetch price for ${asset.symbol}:`, error);
					}
					return {
						assetId: asset.id,
						price: 0,
						currency: 'USD'
					};
				});

			const prices = await Promise.all(pricePromises);
			console.log('All fetched prices:', prices);

			// Update the assetPrices map
			const newPricesMap = new Map();
			prices.forEach(({ assetId, price, currency }) => {
				newPricesMap.set(assetId, { price, currency });
			});

			this.assetPrices = newPricesMap;
			this.pricesLoaded = true;
			devLog.debug('Updated assetPrices Map:', Array.from(this.assetPrices.entries()));
			devLog.debug('=== fetchAllCurrentPrices END ===');

			return this.assetPrices;
		} catch (error) {
			devLog.error('Failed to fetch current prices:', error);
			throw error;
		}
	}

	getCurrentPrice(asset: Asset): number {
		if (asset.type === 'cash') {
			return 1; // Cash has no price, value is just quantity
		}
		const priceData = this.assetPrices.get(asset.id);
		devLog.debug(
			`getCurrentPrice debug - Asset ID: ${asset.id}, Symbol: ${asset.symbol}, Price data:`,
			priceData,
			`Price: ${priceData?.price || 0}`
		);
		return priceData?.price || 0;
	}

	getPriceMap(): Map<number, { price: number; currency: string }> {
		return this.assetPrices;
	}

	isPricesLoaded(): boolean {
		return this.pricesLoaded;
	}

	setPrices(pricesMap: Map<number, { price: number; currency: string }>): void {
		devLog.info(`PriceManagementService: Set ${pricesMap.size} prices`);
		this.assetPrices = pricesMap;
		this.pricesLoaded = true;
	}

	updatePrices(newPrices: Map<number, { price: number; currency: string }>): void {
		this.assetPrices = newPrices;
		this.pricesLoaded = true;
	}

	reset(): void {
		this.assetPrices.clear();
		this.pricesLoaded = false;
	}
}
