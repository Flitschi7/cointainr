import type { Asset, PriceResponse } from '$lib/types';
import { devLog } from '$lib/utils/logger';
import * as enhancedApi from './enhancedApi';

// A retained quote is only valid for the instrument it was loaded for.
function quoteIdentity(asset: Asset): string {
	return `${asset.type}:${asset.symbol ?? ''}`;
}

export class PriceManagementService {
	private assetPrices: Map<number, { price: number; currency: string }> = new Map();
	private quoteIdentities: Map<number, string> = new Map();
	private pricesLoaded = false;
	private loadRevision = 0;

	/** Resolves to null when a newer load or price update superseded this one. */
	async fetchAllCurrentPrices(
		assets: Asset[],
		forceRefresh: boolean = false
	): Promise<Map<number, { price: number; currency: string }> | null> {
		const revision = ++this.loadRevision;
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

						if (
							priceData &&
							priceData.source !== 'error' &&
							Number.isFinite(priceData.price) &&
							priceData.price >= 0 &&
							priceData.currency
						) {
							return {
								assetId: asset.id,
								price: priceData.price,
								currency: priceData.currency
							};
						}
					} catch (error) {
						console.error(`Failed to fetch price for ${asset.symbol}:`, error);
					}
					return null;
				});

			const prices = await Promise.all(pricePromises);
			if (revision !== this.loadRevision) return null;
			console.log('All fetched prices:', prices);

			// Update the assetPrices map
			const newPricesMap = new Map<number, { price: number; currency: string }>();
			for (const asset of assets) {
				const previous = this.assetPrices.get(asset.id);
				if (
					asset.type !== 'cash' &&
					this.quoteIdentities.get(asset.id) === quoteIdentity(asset) &&
					previous &&
					Number.isFinite(previous.price) &&
					previous.price >= 0 &&
					previous.currency
				) {
					newPricesMap.set(asset.id, previous);
				}
			}
			prices.forEach((quote) => {
				if (quote)
					newPricesMap.set(quote.assetId, { price: quote.price, currency: quote.currency });
			});

			this.assetPrices = newPricesMap;
			this.recordQuoteIdentities(assets);
			this.pricesLoaded = true;
			devLog.debug('Updated assetPrices Map:', Array.from(this.assetPrices.entries()));
			devLog.debug('=== fetchAllCurrentPrices END ===');

			return this.assetPrices;
		} catch (error) {
			devLog.error('Failed to fetch current prices:', error);
			throw error;
		}
	}

	getPriceMap(): Map<number, { price: number; currency: string }> {
		return this.assetPrices;
	}

	isPricesLoaded(): boolean {
		return this.pricesLoaded;
	}

	/** `assets` are the holdings the prices were loaded for; their quotes may be retained offline. */
	setPrices(pricesMap: Map<number, { price: number; currency: string }>, assets: Asset[]): void {
		this.loadRevision += 1;
		devLog.info(`PriceManagementService: Set ${pricesMap.size} prices`);
		this.assetPrices = pricesMap;
		this.recordQuoteIdentities(assets);
		this.pricesLoaded = true;
	}

	/** Prices without known holdings are used as given but never retained offline. */
	updatePrices(newPrices: Map<number, { price: number; currency: string }>): void {
		this.loadRevision += 1;
		this.assetPrices = newPrices;
		this.quoteIdentities = new Map();
		this.pricesLoaded = true;
	}

	reset(): void {
		this.loadRevision += 1;
		this.assetPrices.clear();
		this.quoteIdentities = new Map();
		this.pricesLoaded = false;
	}

	private recordQuoteIdentities(assets: Asset[]): void {
		this.quoteIdentities = new Map(
			assets
				.filter((asset) => this.assetPrices.has(asset.id))
				.map((asset) => [asset.id, quoteIdentity(asset)])
		);
	}
}
