import type { Asset } from '$lib/types';
import { convertCurrency } from './api';

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

		for (const asset of assets) {
			let value = 0;

			if (asset.type === 'cash') {
				// Cash - assume it's in EUR, convert if needed
				value = asset.quantity;
				if (targetCurrency !== 'EUR') {
					const conversion = await convertCurrency('EUR', targetCurrency, value, false);
					value = conversion.converted;
				}
			} else {
				const currentPrice = this.getCurrentPrice(asset);
				if (currentPrice > 0) {
					const rawValue = currentPrice * asset.quantity;

					// Get the currency of the price and convert to target currency
					const priceData = this.assetPrices.get(asset.id);
					const priceCurrency = priceData?.currency || 'USD';

					if (priceCurrency !== targetCurrency) {
						const conversion = await convertCurrency(
							priceCurrency,
							targetCurrency,
							rawValue,
							false
						);
						value = conversion.converted;
					} else {
						value = rawValue;
					}
				}
			}

			total += value;
		}

		return total;
	}

	async calculateTotalYield(assets: Asset[], targetCurrency: string): Promise<number> {
		let total = 0;

		for (const asset of assets) {
			let yield_ = 0;

			if (asset.type !== 'cash') {
				const currentPrice = this.getCurrentPrice(asset);
				const purchasePrice = asset.purchase_price;

				if (currentPrice > 0 && purchasePrice && purchasePrice > 0) {
					const currentValue = currentPrice * asset.quantity;
					const investmentValue = purchasePrice * asset.quantity;
					let yieldValue = currentValue - investmentValue;

					// Convert to target currency
					const priceData = this.assetPrices.get(asset.id);
					const priceCurrency = priceData?.currency || 'USD';

					if (priceCurrency !== targetCurrency) {
						const conversion = await convertCurrency(
							priceCurrency,
							targetCurrency,
							yieldValue,
							false
						);
						yieldValue = conversion.converted;
					}

					yield_ = yieldValue;
				}
			}

			total += yield_;
		}

		return total;
	}

	async calculateTotalPerformance(assets: Asset[], targetCurrency: string): Promise<number> {
		let totalCurrentValue = 0;
		let totalInvestment = 0;

		for (const asset of assets) {
			if (asset.type === 'cash') {
				continue; // Cash doesn't contribute to performance calculation
			}

			const currentPrice = this.getCurrentPrice(asset);
			const purchasePrice = asset.purchase_price;

			if (currentPrice > 0 && purchasePrice && purchasePrice > 0) {
				let currentValue = currentPrice * asset.quantity;
				let investmentValue = purchasePrice * asset.quantity;

				// Convert both values to the target currency
				const priceData = this.assetPrices.get(asset.id);
				const priceCurrency = priceData?.currency || 'USD';

				if (priceCurrency !== targetCurrency) {
					const currentConversion = await convertCurrency(
						priceCurrency,
						targetCurrency,
						currentValue,
						false
					);
					currentValue = currentConversion.converted;

					const investmentConversion = await convertCurrency(
						priceCurrency,
						targetCurrency,
						investmentValue,
						false
					);
					investmentValue = investmentConversion.converted;
				}

				totalCurrentValue += currentValue;
				totalInvestment += investmentValue;
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
