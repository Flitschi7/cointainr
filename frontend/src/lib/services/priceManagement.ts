import type { Asset, Quote } from '$lib/types';
import { devLog } from '$lib/utils/logger';
import * as enhancedApi from './enhancedApi';
import { isValidQuote } from './portfolioCalculations';

// A retained quote is only valid for the instrument it was loaded for.
function quoteIdentity(asset: Asset): string {
	return `${asset.type}:${asset.symbol ?? ''}`;
}

export class PriceManagementService {
	private assetPrices: Map<number, Quote> = new Map();
	private quoteIdentities: Map<number, string> = new Map();
	private pricesLoaded = false;
	private loadRevision = 0;

	/** Resolves to null when a newer load or price update superseded this one. */
	async fetchAllCurrentPrices(
		assets: Asset[],
		forceRefresh: boolean = false
	): Promise<Map<number, Quote> | null> {
		const revision = ++this.loadRevision;
		const holdings = assets.filter((asset) => asset.type !== 'cash');
		devLog.debug(`=== fetchAllCurrentPrices START (forceRefresh: ${forceRefresh}) ===`);
		devLog.debug('Non-cash assets to fetch prices for:', holdings);

		try {
			const pricePromises = holdings.map(async (asset) => {
				try {
					// Use the enhanced API with cache-first approach
					const priceData = await enhancedApi.getPrice(
						asset.symbol || '',
						asset.type as 'stock' | 'crypto',
						{
							forceRefresh
						}
					);

					devLog.debug(`Price data for ${asset.symbol}:`, priceData);

					if (priceData && priceData.source !== 'error' && isValidQuote(priceData)) {
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

			// Update the assetPrices map
			const newPricesMap = new Map<number, Quote>();
			for (const asset of holdings) {
				const previous = this.assetPrices.get(asset.id);
				if (this.quoteIdentities.get(asset.id) === quoteIdentity(asset) && isValidQuote(previous)) {
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

	getPriceMap(): Map<number, Quote> {
		return this.assetPrices;
	}

	isPricesLoaded(): boolean {
		return this.pricesLoaded;
	}

	/** `assets` are the holdings the prices were loaded for; their quotes may be retained offline. */
	setPrices(pricesMap: Map<number, Quote>, assets: Asset[]): void {
		this.loadRevision += 1;
		devLog.info(`PriceManagementService: Set ${pricesMap.size} prices`);
		this.assetPrices = pricesMap;
		this.recordQuoteIdentities(assets);
		this.pricesLoaded = true;
	}

	/** Prices without known holdings are used as given but never retained offline. */
	updatePrices(newPrices: Map<number, Quote>): void {
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
