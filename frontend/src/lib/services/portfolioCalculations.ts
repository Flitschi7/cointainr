import type { Asset } from '$lib/types';
import * as enhancedApi from './enhancedApi';

export interface PortfolioTotals {
	totalValue: number | null;
	totalYield: number | null;
	totalPerformance: number | null;
	currency: string;
}

export interface PositionValuation {
	currentPrice: number | null;
	purchasePrice: number | null;
	value: number | null;
	investmentValue: number | null;
	yield: number | null;
	performance: number | null;
}

export interface PortfolioValuation {
	positions: Map<number, PositionValuation>;
	totals: PortfolioTotals;
}

export type PortfolioSortField =
	| 'location'
	| 'asset'
	| 'type'
	| 'currentPrice'
	| 'value'
	| 'quantity'
	| 'purchasePrice'
	| 'performance'
	| 'yield';

export function sortValuedAssets(
	assets: Asset[],
	positions: Map<number, PositionValuation>,
	field: PortfolioSortField | null,
	direction: 'asc' | 'desc'
): Asset[] {
	if (!field) return [...assets];
	const getValue = (asset: Asset): string | number | null => {
		switch (field) {
			case 'location':
				return asset.name || '';
			case 'asset':
				return asset.assetname || asset.symbol || '';
			case 'type':
				return asset.type;
			case 'quantity':
				return asset.type === 'cash' ? null : finiteOrNull(asset.quantity);
			default:
				if (asset.type === 'cash' && (field === 'yield' || field === 'performance')) return null;
				return positions.get(asset.id)?.[field] ?? null;
		}
	};
	return [...assets].sort((first, second) => {
		const firstValue = getValue(first);
		const secondValue = getValue(second);
		if (firstValue === null) return secondValue === null ? 0 : 1;
		if (secondValue === null) return -1;
		const comparison =
			typeof firstValue === 'string' && typeof secondValue === 'string'
				? firstValue.localeCompare(secondValue)
				: Number(firstValue) - Number(secondValue);
		return direction === 'asc' ? comparison : -comparison;
	});
}

function finiteOrNull(value: number): number | null {
	return Number.isFinite(value) ? value : null;
}

function sumAmounts(values: (number | null)[]): number | null {
	let total = 0;
	for (const value of values) {
		if (value === null) return null;
		total += value;
	}
	return finiteOrNull(total);
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
		return priceData?.price ?? 0;
	}

	private async convertAmount(amount: number, from: string, to: string): Promise<number | null> {
		if (!from || !to || !Number.isFinite(amount)) return null;
		try {
			const conversion = await enhancedApi.convertCurrency(from, to, amount, {
				forceRefresh: false
			});
			if (
				conversion.source === 'error' ||
				conversion.from !== from ||
				conversion.to !== to ||
				conversion.amount !== amount ||
				!Number.isFinite(conversion.rate) ||
				conversion.rate <= 0 ||
				!Number.isFinite(conversion.converted)
			)
				return null;
			const expected = amount * conversion.rate;
			const tolerance =
				Number.EPSILON * 8 * Math.max(1, Math.abs(expected), Math.abs(conversion.converted));
			if (
				!Number.isFinite(expected) ||
				(amount === 0 && conversion.converted !== 0) ||
				Math.abs(conversion.converted - expected) > tolerance
			)
				return null;
			return conversion.converted;
		} catch {
			return null;
		}
	}

	async calculateTotalValue(assets: Asset[], targetCurrency: string): Promise<number | null> {
		return (await this.calculatePortfolioTotals(assets, targetCurrency)).totalValue;
	}

	async calculateTotalYield(assets: Asset[], targetCurrency: string): Promise<number | null> {
		return (await this.calculatePortfolioTotals(assets, targetCurrency)).totalYield;
	}

	async calculateTotalPerformance(assets: Asset[], targetCurrency: string): Promise<number | null> {
		return (await this.calculatePortfolioTotals(assets, targetCurrency)).totalPerformance;
	}

	private async calculatePosition(
		asset: Asset,
		targetCurrency: string
	): Promise<PositionValuation> {
		if (asset.type === 'cash') {
			return {
				currentPrice: null,
				purchasePrice: null,
				value: await this.convertAmount(asset.quantity, asset.currency || '', targetCurrency),
				investmentValue: 0,
				yield: 0,
				performance: 0
			};
		}

		const quote = this.assetPrices.get(asset.id);
		const hasQuote =
			quote !== undefined && Number.isFinite(quote.price) && quote.price >= 0 && !!quote.currency;
		const purchasePrice = asset.purchase_price;
		const purchaseCurrency = asset.buy_currency || asset.currency;
		const hasPurchase =
			purchasePrice !== null &&
			Number.isFinite(purchasePrice) &&
			purchasePrice >= 0 &&
			!!purchaseCurrency;
		const [value, investmentValue] = await Promise.all([
			hasQuote
				? this.convertAmount(quote.price * asset.quantity, quote.currency, targetCurrency)
				: null,
			hasPurchase
				? this.convertAmount(purchasePrice * asset.quantity, purchaseCurrency, targetCurrency)
				: null
		]);
		const currentUnitPrice =
			asset.quantity === 0
				? hasQuote
					? await this.convertAmount(quote.price, quote.currency, targetCurrency)
					: null
				: value === null
					? null
					: finiteOrNull(value / asset.quantity);
		const purchaseUnitPrice =
			asset.quantity === 0
				? hasPurchase
					? await this.convertAmount(purchasePrice, purchaseCurrency, targetCurrency)
					: null
				: investmentValue === null
					? null
					: finiteOrNull(investmentValue / asset.quantity);
		const profitLoss =
			value !== null && investmentValue !== null ? finiteOrNull(value - investmentValue) : null;
		return {
			currentPrice: currentUnitPrice,
			purchasePrice: purchaseUnitPrice,
			value,
			investmentValue,
			yield: profitLoss,
			performance:
				profitLoss !== null && investmentValue !== null && investmentValue !== 0
					? finiteOrNull((profitLoss / investmentValue) * 100)
					: null
		};
	}

	async calculatePortfolioValuation(
		assets: Asset[],
		targetCurrency: string
	): Promise<PortfolioValuation> {
		const positions = new Map(
			await Promise.all(
				assets.map(
					async (asset) => [asset.id, await this.calculatePosition(asset, targetCurrency)] as const
				)
			)
		);
		const holdings = assets.filter((asset) => asset.type !== 'cash');
		const currentValue = sumAmounts(
			holdings.map((asset) => positions.get(asset.id)?.value ?? null)
		);
		const investment = sumAmounts(
			holdings.map((asset) => positions.get(asset.id)?.investmentValue ?? null)
		);
		const totalYield =
			currentValue !== null && investment !== null ? finiteOrNull(currentValue - investment) : null;
		return {
			positions,
			totals: {
				totalValue: sumAmounts(assets.map((asset) => positions.get(asset.id)?.value ?? null)),
				totalYield,
				totalPerformance:
					holdings.length === 0
						? 0
						: totalYield !== null && investment !== null && investment !== 0
							? finiteOrNull((totalYield / investment) * 100)
							: null,
				currency: targetCurrency
			}
		};
	}

	async calculatePortfolioTotals(
		assets: Asset[],
		targetCurrency: string
	): Promise<PortfolioTotals> {
		return (await this.calculatePortfolioValuation(assets, targetCurrency)).totals;
	}

	// Update the price map when new prices are fetched
	updatePrices(newPrices: Map<number, { price: number; currency: string }>): void {
		this.assetPrices = newPrices;
	}
}
