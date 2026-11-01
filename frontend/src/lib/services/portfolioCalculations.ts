import type { Asset, Quote } from '$lib/types';
import * as enhancedApi from './enhancedApi';

/** A usable quote has a finite, non-negative price and a known currency; zero is valid. */
export function isValidQuote(quote: Quote | null | undefined): quote is Quote {
	return !!quote && Number.isFinite(quote.price) && quote.price >= 0 && !!quote.currency;
}

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
	private assetPrices: Map<number, Quote>;

	constructor(assetPrices: Map<number, Quote>) {
		this.assetPrices = assetPrices;
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

	/**
	 * Per-unit amount in the target currency. Derived from the position total, except for a
	 * zero quantity, where the unit amount is converted directly to avoid dividing by zero.
	 */
	private async unitAmount(
		unit: { amount: number; currency: string } | null,
		total: number | null,
		quantity: number,
		targetCurrency: string
	): Promise<number | null> {
		if (quantity !== 0) return total === null ? null : finiteOrNull(total / quantity);
		return unit ? this.convertAmount(unit.amount, unit.currency, targetCurrency) : null;
	}

	private async calculatePosition(
		asset: Asset,
		targetCurrency: string
	): Promise<PositionValuation> {
		if (asset.type === 'cash') {
			// Cash has a value but no cost basis, so its investment metrics are inapplicable.
			return {
				currentPrice: null,
				purchasePrice: null,
				value: await this.convertAmount(asset.quantity, asset.currency || '', targetCurrency),
				investmentValue: null,
				yield: null,
				performance: null
			};
		}

		const quote = this.assetPrices.get(asset.id);
		const currentUnit = isValidQuote(quote)
			? { amount: quote.price, currency: quote.currency }
			: null;
		const purchasePrice = asset.purchase_price;
		const purchaseCurrency = asset.buy_currency || asset.currency;
		const purchaseUnit =
			purchasePrice !== null &&
			Number.isFinite(purchasePrice) &&
			purchasePrice >= 0 &&
			purchaseCurrency
				? { amount: purchasePrice, currency: purchaseCurrency }
				: null;
		const [value, investmentValue] = await Promise.all(
			[currentUnit, purchaseUnit].map((unit) =>
				unit
					? this.convertAmount(unit.amount * asset.quantity, unit.currency, targetCurrency)
					: null
			)
		);
		const [currentUnitPrice, purchaseUnitPrice] = await Promise.all([
			this.unitAmount(currentUnit, value, asset.quantity, targetCurrency),
			this.unitAmount(purchaseUnit, investmentValue, asset.quantity, targetCurrency)
		]);
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
	updatePrices(newPrices: Map<number, Quote>): void {
		this.assetPrices = newPrices;
	}
}
