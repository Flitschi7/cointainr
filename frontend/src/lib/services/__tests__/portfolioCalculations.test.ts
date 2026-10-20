import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Asset } from '$lib/types';
import { cacheService } from '../cacheService';
import { PortfolioCalculationService, sortValuedAssets } from '../portfolioCalculations';
import { PriceManagementService } from '../priceManagement';

const euroCash: Asset = {
	id: 1,
	type: 'cash',
	name: 'Test cash',
	quantity: 20,
	symbol: null,
	currency: 'EUR',
	purchase_price: null,
	buy_currency: null
};

const euroHolding: Asset = {
	...euroCash,
	id: 3,
	type: 'stock',
	symbol: 'TEST',
	quantity: 2,
	purchase_price: 80,
	buy_currency: 'EUR'
};

describe('Portfolio totals', () => {
	beforeEach(() => {
		cacheService.clearAllCache();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
		cacheService.clearAllCache();
	});

	it('does not present unconverted cash as a complete target-currency total', async () => {
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('FX unavailable')));
		const dollarCash: Asset = { ...euroCash, id: 2, quantity: 100, currency: 'USD' };
		const service = new PortfolioCalculationService(new Map());

		const totals = await service.calculatePortfolioTotals([euroCash, dollarCash], 'EUR');

		expect(totals.totalValue).toBeNull();
	});

	it('provides position metrics and portfolio totals in the same display currency', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () =>
				Response.json({ from: 'USD', to: 'EUR', amount: 200, converted: 180, rate: 0.9 })
			)
		);
		const service = new PortfolioCalculationService(
			new Map([[euroHolding.id, { price: 100, currency: 'USD' }]])
		);

		const valuation = await service.calculatePortfolioValuation(
			[euroHolding, { ...euroCash, quantity: 95 }],
			'EUR'
		);

		expect(valuation.positions.get(euroHolding.id)).toEqual({
			currentPrice: 90,
			purchasePrice: 80,
			value: 180,
			investmentValue: 160,
			yield: 20,
			performance: 12.5
		});
		expect(valuation.positions.get(euroCash.id)?.value).toBe(95);
		expect(valuation.totals).toEqual({
			totalValue: 275,
			totalYield: 20,
			totalPerformance: 12.5,
			currency: 'EUR'
		});
	});

	it.each([
		{ direction: 'asc' as const, ids: [4, 5, 2, 1, 3] },
		{ direction: 'desc' as const, ids: [1, 2, 5, 4, 3] }
	])(
		'sorts converted values with unavailable positions last ($direction)',
		async ({ direction, ids }) => {
			vi.stubGlobal(
				'fetch',
				vi.fn(async () =>
					Response.json({ from: 'USD', to: 'EUR', amount: 100, converted: 90, rate: 0.9 })
				)
			);
			const assets = [
				{ ...euroCash, quantity: 95 },
				{ ...euroCash, id: 2, quantity: 100, currency: 'USD' },
				{ ...euroCash, id: 3, currency: null },
				{ ...euroCash, id: 4, quantity: -5 },
				{ ...euroCash, id: 5, quantity: 0 }
			];
			const valuation = await new PortfolioCalculationService(
				new Map()
			).calculatePortfolioValuation(assets, 'EUR');

			expect(
				sortValuedAssets(assets, valuation.positions, 'value', direction).map((asset) => asset.id)
			).toEqual(ids);
		}
	);

	it('converts quote and purchase currencies independently before calculating returns', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async (input: string | URL | Request) => {
				const url = new URL(String(input));
				const amount = Number(url.searchParams.get('amount'));
				return Response.json({
					from: 'USD',
					to: 'EUR',
					amount,
					converted: amount * 0.9,
					rate: 0.9,
					source: 'test'
				});
			})
		);
		const holding: Asset = {
			...euroCash,
			id: 3,
			type: 'stock',
			symbol: 'TEST',
			quantity: 2,
			currency: 'USD',
			purchase_price: 80,
			buy_currency: 'EUR'
		};
		const service = new PortfolioCalculationService(
			new Map([[holding.id, { price: 100, currency: 'USD' }]])
		);

		const totals = await service.calculatePortfolioTotals([holding], 'EUR');

		expect(totals).toEqual({
			totalValue: 180,
			totalYield: 20,
			totalPerformance: 12.5,
			currency: 'EUR'
		});
	});

	it.each([
		{ field: 'currentPrice', direction: 'asc', ids: [3, 6, 4, 7, 5] },
		{ field: 'currentPrice', direction: 'desc', ids: [4, 7, 6, 3, 5] },
		{ field: 'purchasePrice', direction: 'asc', ids: [4, 3, 7, 5, 6] },
		{ field: 'purchasePrice', direction: 'desc', ids: [5, 3, 7, 4, 6] },
		{ field: 'yield', direction: 'asc', ids: [3, 7, 4, 5, 6] },
		{ field: 'yield', direction: 'desc', ids: [4, 7, 3, 5, 6] },
		{ field: 'performance', direction: 'asc', ids: [3, 7, 4, 5, 6] },
		{ field: 'performance', direction: 'desc', ids: [7, 3, 4, 5, 6] }
	] as const)(
		'sorts $field $direction without conflating zero and missing data',
		async ({ field, direction, ids }) => {
			const assets = [
				{ ...euroHolding, quantity: 1, purchase_price: 10 },
				{ ...euroHolding, id: 4, quantity: 1, purchase_price: 0 },
				{ ...euroHolding, id: 5, quantity: 1, purchase_price: 20 },
				{ ...euroHolding, id: 6, quantity: 1, purchase_price: null },
				{ ...euroHolding, id: 7, quantity: 1, purchase_price: 10 }
			];
			const prices = new Map([
				[3, { price: 0, currency: 'EUR' }],
				[4, { price: 10, currency: 'EUR' }],
				[6, { price: 5, currency: 'EUR' }],
				[7, { price: 10, currency: 'EUR' }]
			]);
			const valuation = await new PortfolioCalculationService(prices).calculatePortfolioValuation(
				assets,
				'EUR'
			);

			expect(
				sortValuedAssets(assets, valuation.positions, field, direction).map((asset) => asset.id)
			).toEqual(ids);
		}
	);

	it('weights aggregate performance by invested value instead of averaging row percentages', async () => {
		const assets = [
			{ ...euroHolding, quantity: 1, purchase_price: 50 },
			{ ...euroHolding, id: 4, quantity: 1, purchase_price: 200 }
		];
		const service = new PortfolioCalculationService(
			new Map([
				[3, { price: 100, currency: 'EUR' }],
				[4, { price: 200, currency: 'EUR' }]
			])
		);

		const valuation = await service.calculatePortfolioValuation(assets, 'EUR');

		expect(valuation.positions.get(3)?.performance).toBe(100);
		expect(valuation.positions.get(4)?.performance).toBe(0);
		expect(valuation.totals).toEqual({
			totalValue: 300,
			totalYield: 50,
			totalPerformance: 20,
			currency: 'EUR'
		});
	});

	it('keeps unit prices available for a zero quantity without dividing by zero', async () => {
		const asset = { ...euroHolding, quantity: 0 };
		const valuation = await new PortfolioCalculationService(
			new Map([[asset.id, { price: 100, currency: 'EUR' }]])
		).calculatePortfolioValuation([asset], 'EUR');

		expect(valuation.positions.get(asset.id)).toEqual({
			currentPrice: 100,
			purchasePrice: 80,
			value: 0,
			investmentValue: 0,
			yield: 0,
			performance: null
		});
		expect(valuation.totals.totalPerformance).toBeNull();
	});

	it.each([undefined, NaN, Infinity])(
		'marks totals unavailable for an unusable quote (%s)',
		async (price) => {
			const prices = new Map<number, { price: number; currency: string }>();
			if (price !== undefined) prices.set(euroHolding.id, { price, currency: 'EUR' });
			const service = new PortfolioCalculationService(prices);

			const totals = await service.calculatePortfolioTotals([euroCash, euroHolding], 'EUR');

			expect(totals).toEqual({
				totalValue: null,
				totalYield: null,
				totalPerformance: null,
				currency: 'EUR'
			});
		}
	);

	it('distinguishes a known zero quote from an unavailable quote', async () => {
		const service = new PortfolioCalculationService(
			new Map([[euroHolding.id, { price: 0, currency: 'EUR' }]])
		);

		const totals = await service.calculatePortfolioTotals([euroHolding], 'EUR');

		expect(totals).toEqual({
			totalValue: 0,
			totalYield: -160,
			totalPerformance: -100,
			currency: 'EUR'
		});
	});

	it('marks overflowed aggregate returns unavailable', async () => {
		const holdings = [
			{ ...euroHolding, quantity: 1 },
			{ ...euroHolding, id: 4, quantity: 1 }
		];
		const service = new PortfolioCalculationService(
			new Map(holdings.map((asset) => [asset.id, { price: Number.MAX_VALUE, currency: 'EUR' }]))
		);

		expect(await service.calculatePortfolioTotals(holdings, 'EUR')).toEqual({
			totalValue: null,
			totalYield: null,
			totalPerformance: null,
			currency: 'EUR'
		});
	});

	it.each([
		{ purchasePrice: null, totalYield: null },
		{ purchasePrice: 0, totalYield: 200 }
	])(
		'distinguishes unknown from zero purchase cost ($purchasePrice)',
		async ({ purchasePrice, totalYield }) => {
			const holding = { ...euroHolding, purchase_price: purchasePrice };
			const service = new PortfolioCalculationService(
				new Map([[holding.id, { price: 100, currency: 'EUR' }]])
			);

			const totals = await service.calculatePortfolioTotals([holding], 'EUR');

			expect(totals).toEqual({
				totalValue: 200,
				totalYield,
				totalPerformance: null,
				currency: 'EUR'
			});
		}
	);

	it('does not force a provider refresh when calculating totals', async () => {
		const requests: URL[] = [];
		vi.stubGlobal(
			'fetch',
			vi.fn(async (input: string | URL | Request) => {
				requests.push(new URL(String(input)));
				return Response.json({ from: 'USD', to: 'EUR', amount: 100, converted: 90, rate: 0.9 });
			})
		);
		const service = new PortfolioCalculationService(new Map());

		const totals = await service.calculatePortfolioTotals(
			[{ ...euroCash, quantity: 100, currency: 'USD' }],
			'EUR'
		);

		expect(totals.totalValue).toBe(90);
		expect(requests.map((url) => url.searchParams.get('force_refresh'))).not.toContain('true');
	});

	it.each([{ converted: null }, { rate: 0 }, { to: 'USD' }, { amount: 999 }])(
		'rejects an unusable FX response (%j)',
		async (invalidFields) => {
			vi.stubGlobal(
				'fetch',
				vi.fn(async () =>
					Response.json({
						from: 'USD',
						to: 'EUR',
						amount: 100,
						converted: 90,
						rate: 0.9,
						...invalidFields
					})
				)
			);
			const service = new PortfolioCalculationService(new Map());

			const totals = await service.calculatePortfolioTotals(
				[{ ...euroCash, quantity: 100, currency: 'USD' }],
				'EUR'
			);

			expect(totals.totalValue).toBeNull();
		}
	);

	it.each([
		{ amount: 100, converted: -90, expected: null },
		{ amount: 100, converted: 89, expected: null },
		{ amount: 0, converted: 1, expected: null },
		{ amount: -100, converted: -90, expected: -90 }
	])(
		'validates FX arithmetic without rejecting negative cash (%j)',
		async ({ amount, converted, expected }) => {
			vi.stubGlobal(
				'fetch',
				vi.fn(async () => Response.json({ from: 'USD', to: 'EUR', amount, converted, rate: 0.9 }))
			);
			const totals = await new PortfolioCalculationService(new Map()).calculatePortfolioTotals(
				[{ ...euroCash, currency: 'USD', quantity: amount }],
				'EUR'
			);
			expect(totals.totalValue).toBe(expected);
		}
	);

	it.each([
		{
			label: 'cash',
			asset: { ...euroCash, currency: null },
			quote: undefined,
			target: 'EUR',
			value: null,
			yield: 0
		},
		{
			label: 'quote',
			asset: euroHolding,
			quote: { price: 100, currency: '' },
			target: 'USD',
			value: null,
			yield: null
		},
		{
			label: 'purchase',
			asset: { ...euroHolding, currency: null, buy_currency: null },
			quote: { price: 100, currency: 'EUR' },
			target: 'EUR',
			value: 200,
			yield: null
		}
	])('does not invent an unknown $label currency', async (scenario) => {
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('FX unavailable')));
		const service = new PortfolioCalculationService(
			new Map(scenario.quote ? [[scenario.asset.id, scenario.quote]] : [])
		);

		const totals = await service.calculatePortfolioTotals([scenario.asset], scenario.target);

		expect(totals).toEqual({
			totalValue: scenario.value,
			totalYield: scenario.yield,
			totalPerformance: scenario.yield === null ? null : 0,
			currency: scenario.target
		});
	});

	it('retains a usable stale FX cache entry when the network is offline', async () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2026-10-20T00:00:00Z'));
		cacheService.set('conversion_USD_EUR_100', {
			from: 'USD',
			to: 'EUR',
			amount: 100,
			converted: 90,
			rate: 0.9,
			source: 'cache'
		});
		vi.setSystemTime(new Date('2026-11-20T00:00:00Z'));
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Offline')));
		const service = new PortfolioCalculationService(new Map());

		const totals = await service.calculatePortfolioTotals(
			[{ ...euroCash, quantity: 100, currency: 'USD' }],
			'EUR'
		);

		expect(totals.totalValue).toBe(90);
	});

	it('keeps market value available when only the purchase conversion fails', async () => {
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('FX unavailable')));
		const service = new PortfolioCalculationService(
			new Map([[euroHolding.id, { price: 100, currency: 'EUR' }]])
		);

		const totals = await service.calculatePortfolioTotals(
			[{ ...euroHolding, buy_currency: 'USD' }],
			'EUR'
		);

		expect(totals).toEqual({
			totalValue: 200,
			totalYield: null,
			totalPerformance: null,
			currency: 'EUR'
		});
	});

	it('returns known zero totals for an empty portfolio', async () => {
		const service = new PortfolioCalculationService(new Map());

		expect(await service.calculatePortfolioTotals([], 'EUR')).toEqual({
			totalValue: 0,
			totalYield: 0,
			totalPerformance: 0,
			currency: 'EUR'
		});
	});

	it('does not let an older quote load replace a completed forced refresh', async () => {
		let releaseOldQuote!: (response: Response) => void;
		let markOldStarted!: () => void;
		const oldStarted = new Promise<void>((resolve) => {
			markOldStarted = resolve;
		});
		vi.stubGlobal(
			'fetch',
			vi.fn((input: string | URL | Request) => {
				if (new URL(String(input)).searchParams.get('force_refresh') === 'true') {
					return Promise.resolve(Response.json({ price: 120, currency: 'EUR' }));
				}
				markOldStarted();
				return new Promise<Response>((resolve) => {
					releaseOldQuote = resolve;
				});
			})
		);
		const prices = new PriceManagementService();
		const oldLoad = prices.fetchAllCurrentPrices([euroHolding]);
		await oldStarted;
		await prices.fetchAllCurrentPrices([euroHolding], true);
		releaseOldQuote(Response.json({ price: 100, currency: 'EUR' }));

		expect((await oldLoad).get(euroHolding.id)?.price).toBe(120);
		expect(prices.getPriceMap().get(euroHolding.id)?.price).toBe(120);
	});

	it.each([0, 100])(
		'retains a known in-memory quote (%s) when refresh fails offline',
		async (price) => {
			vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Offline')));
			const prices = new PriceManagementService();
			prices.setPrices(new Map([[euroHolding.id, { price, currency: 'EUR' }]]));

			const refreshed = await prices.fetchAllCurrentPrices([euroHolding], true);

			expect(refreshed.get(euroHolding.id)).toEqual({ price, currency: 'EUR' });
		}
	);

	it('does not turn a failed quote request into a known zero price', async () => {
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Quote unavailable')));
		const prices = await new PriceManagementService().fetchAllCurrentPrices([euroHolding]);
		const service = new PortfolioCalculationService(prices);

		const totals = await service.calculatePortfolioTotals([euroHolding], 'USD');

		expect(totals.totalValue).toBeNull();
	});
});
