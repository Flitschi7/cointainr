import type { Asset } from '$lib/types';
import * as enhancedApi from './enhancedApi';

export interface PortfolioTotals {
	totalValue: number;
	totalYield: number;
	totalPerformance: number;
	currency: string;
}

export class PortfolioCalculationService {
	private assetPrices: Map<number, { price: number; currency: string }>;

	constructor(assetPrices: Map<number, { price: number; currency: string }>) {
		this.assetPrices = assetPrices;
	}

	getCurrentPrice(asset: Asset): number {
		if (asset.type === 'cash') {
			return 1; // Cash has no price, value is just quantity
		}
		const priceData = this.assetPrices.get(asset.id);
		return priceData?.price || 0;
	}

	async calculateTotalValue(assets: Asset[], targetCurrency: string): Promise<number> {
		let total = 0;

		// Prepare batch conversion data
		const amounts: number[] = [];
		const fromCurrencies: string[] = [];
		const toCurrencies: string[] = [];
		const assetIndices: number[] = [];

		// First pass: collect all conversion requests
		for (let i = 0; i < assets.length; i++) {
			const asset = assets[i];
			let value = 0;
			let currency = '';

			if (asset.type === 'cash') {
				// Cash - use the actual currency of the cash asset
				value = asset.quantity;
				currency = asset.currency || 'EUR'; // Fallback to EUR if currency is null
			} else {
				const currentPrice = this.getCurrentPrice(asset);
				if (currentPrice > 0) {
					value = currentPrice * asset.quantity;
					// Get the currency of the price
					const priceData = this.assetPrices.get(asset.id);
					currency = priceData?.currency || 'USD';
					console.log(
						`PortfolioCalculationService - Asset ${asset.id} (${asset.symbol}): price=${currentPrice}, quantity=${asset.quantity}, value=${value}, currency=${currency}, targetCurrency=${targetCurrency}`
					);
				} else {
					continue; // Skip assets with no price
				}
			}

			// If currency is different from target, add to batch conversion
			if (currency !== targetCurrency) {
				amounts.push(value);
				fromCurrencies.push(currency);
				toCurrencies.push(targetCurrency);
				assetIndices.push(i);
				console.log(
					`PortfolioCalculationService - Added to conversion batch: ${value} ${currency} -> ${targetCurrency}`
				);
			} else {
				// No conversion needed, add directly to total
				total += value;
				console.log(
					`PortfolioCalculationService - Added directly to total: ${value} ${currency} (no conversion needed)`
				);
			}
		}

		// Second pass: perform batch conversion if needed
		if (amounts.length > 0) {
			console.log('PortfolioCalculationService - Batch conversion needed:', {
				amounts,
				fromCurrencies,
				toCurrencies,
				targetCurrency
			});

			try {
				// Use batch conversion for better performance
				const conversions = await enhancedApi.batchConvertCurrency(
					amounts,
					fromCurrencies,
					toCurrencies,
					{ forceRefresh: false }
				);

				console.log('PortfolioCalculationService - Batch conversion results:', conversions);

				// Add converted values to total
				conversions.forEach((conversion) => {
					total += conversion.converted;
				});
			} catch (error) {
				console.error('Error in batch currency conversion:', error);

				// Fallback to individual conversions if batch fails
				for (let i = 0; i < amounts.length; i++) {
					try {
						const conversion = await enhancedApi.convertCurrency(
							fromCurrencies[i],
							toCurrencies[i],
							amounts[i],
							{ forceRefresh: false }
						);
						total += conversion.converted;
					} catch (convError) {
						console.error(
							`Error converting ${fromCurrencies[i]} to ${toCurrencies[i]}:`,
							convError
						);
						// Add unconverted amount as fallback
						total += amounts[i];
					}
				}
			}
		}

		return total;
	}

	async calculateTotalYield(assets: Asset[], targetCurrency: string): Promise<number> {
		let total = 0;

		// Prepare batch conversion data
		const amounts: number[] = [];
		const fromCurrencies: string[] = [];
		const toCurrencies: string[] = [];

		// First pass: collect all yield values that need conversion
		for (const asset of assets) {
			if (asset.type === 'cash') {
				continue; // Cash doesn't contribute to yield
			}

			const currentPrice = this.getCurrentPrice(asset);
			const purchasePrice = asset.purchase_price;

			if (currentPrice > 0 && purchasePrice && purchasePrice > 0) {
				const currentValue = currentPrice * asset.quantity;
				const investmentValue = purchasePrice * asset.quantity;
				const yieldValue = currentValue - investmentValue;

				// Get the currency of the price
				const priceData = this.assetPrices.get(asset.id);
				const priceCurrency = priceData?.currency || 'USD';

				// If currency is different from target, add to batch conversion
				if (priceCurrency !== targetCurrency) {
					amounts.push(yieldValue);
					fromCurrencies.push(priceCurrency);
					toCurrencies.push(targetCurrency);
				} else {
					// No conversion needed, add directly to total
					total += yieldValue;
				}
			}
		}

		// Second pass: perform batch conversion if needed
		if (amounts.length > 0) {
			try {
				// Use batch conversion for better performance
				const conversions = await enhancedApi.batchConvertCurrency(
					amounts,
					fromCurrencies,
					toCurrencies,
					{ forceRefresh: false }
				);

				// Add converted values to total
				conversions.forEach((conversion) => {
					total += conversion.converted;
				});
			} catch (error) {
				console.error('Error in batch currency conversion for yields:', error);

				// Fallback to individual conversions if batch fails
				for (let i = 0; i < amounts.length; i++) {
					try {
						const conversion = await enhancedApi.convertCurrency(
							fromCurrencies[i],
							toCurrencies[i],
							amounts[i],
							{ forceRefresh: false }
						);
						total += conversion.converted;
					} catch (convError) {
						console.error(
							`Error converting yield from ${fromCurrencies[i]} to ${toCurrencies[i]}:`,
							convError
						);
						// Add unconverted amount as fallback
						total += amounts[i];
					}
				}
			}
		}

		return total;
	}

	async calculateTotalPerformance(assets: Asset[], targetCurrency: string): Promise<number> {
		let totalCurrentValue = 0;
		let totalInvestment = 0;

		// Prepare batch conversion data for current values
		const currentAmounts: number[] = [];
		const investmentAmounts: number[] = [];
		const fromCurrencies: string[] = [];
		const toCurrencies: string[] = [];

		// First pass: collect all values that need conversion
		for (const asset of assets) {
			if (asset.type === 'cash') {
				continue; // Cash doesn't contribute to performance calculation
			}

			const currentPrice = this.getCurrentPrice(asset);
			const purchasePrice = asset.purchase_price;

			if (currentPrice > 0 && purchasePrice && purchasePrice > 0) {
				const currentValue = currentPrice * asset.quantity;
				const investmentValue = purchasePrice * asset.quantity;

				// Get the currency of the price
				const priceData = this.assetPrices.get(asset.id);
				const priceCurrency = priceData?.currency || 'USD';

				// If currency is different from target, add to batch conversion
				if (priceCurrency !== targetCurrency) {
					currentAmounts.push(currentValue);
					investmentAmounts.push(investmentValue);
					fromCurrencies.push(priceCurrency);
					toCurrencies.push(targetCurrency);
				} else {
					// No conversion needed, add directly to totals
					totalCurrentValue += currentValue;
					totalInvestment += investmentValue;
				}
			}
		}

		// Second pass: perform batch conversion if needed
		if (currentAmounts.length > 0) {
			try {
				// Use batch conversion for current values
				const currentConversions = await enhancedApi.batchConvertCurrency(
					currentAmounts,
					fromCurrencies,
					toCurrencies,
					{ forceRefresh: false }
				);

				// Use batch conversion for investment values
				const investmentConversions = await enhancedApi.batchConvertCurrency(
					investmentAmounts,
					fromCurrencies,
					toCurrencies,
					{ forceRefresh: false }
				);

				// Add converted values to totals
				for (let i = 0; i < currentConversions.length; i++) {
					totalCurrentValue += currentConversions[i].converted;
					totalInvestment += investmentConversions[i].converted;
				}
			} catch (error) {
				console.error('Error in batch currency conversion for performance calculation:', error);

				// Fallback to individual conversions if batch fails
				for (let i = 0; i < currentAmounts.length; i++) {
					try {
						// Convert current value
						const currentConversion = await enhancedApi.convertCurrency(
							fromCurrencies[i],
							toCurrencies[i],
							currentAmounts[i],
							{ forceRefresh: false }
						);
						totalCurrentValue += currentConversion.converted;

						// Convert investment value
						const investmentConversion = await enhancedApi.convertCurrency(
							fromCurrencies[i],
							toCurrencies[i],
							investmentAmounts[i],
							{ forceRefresh: false }
						);
						totalInvestment += investmentConversion.converted;
					} catch (convError) {
						console.error(
							`Error converting performance values from ${fromCurrencies[i]} to ${toCurrencies[i]}:`,
							convError
						);
						// Add unconverted amounts as fallback
						totalCurrentValue += currentAmounts[i];
						totalInvestment += investmentAmounts[i];
					}
				}
			}
		}

		if (totalInvestment === 0) {
			return 0;
		}

		return ((totalCurrentValue - totalInvestment) / totalInvestment) * 100;
	}

	async calculatePortfolioTotals(
		assets: Asset[],
		targetCurrency: string
	): Promise<PortfolioTotals> {
		const [totalValue, totalYield, totalPerformance] = await Promise.all([
			this.calculateTotalValue(assets, targetCurrency),
			this.calculateTotalYield(assets, targetCurrency),
			this.calculateTotalPerformance(assets, targetCurrency)
		]);

		return {
			totalValue,
			totalYield,
			totalPerformance,
			currency: targetCurrency
		};
	}

	// Update the price map when new prices are fetched
	updatePrices(newPrices: Map<number, { price: number; currency: string }>): void {
		this.assetPrices = newPrices;
	}
}
