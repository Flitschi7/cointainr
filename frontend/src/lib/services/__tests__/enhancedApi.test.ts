/**
 * Tests for the enhanced API service with cache-first approach
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as api from '../api';
import * as enhancedApi from '../enhancedApi';
import { cacheService } from '../cacheService';

// Mock the original API functions
vi.mock('../api', () => ({
	getStockPrice: vi.fn(),
	getCryptoPrice: vi.fn(),
	convertCurrency: vi.fn(),
	getConversionRate: vi.fn(),
	getAssets: vi.fn(),
	refreshAllPrices: vi.fn(),
	clearPriceCache: vi.fn(),
	clearConversionCache: vi.fn(),
	getCacheStats: vi.fn(),
	getConversionCacheStats: vi.fn(),
	getAssetCacheStatus: vi.fn()
}));

describe('Enhanced API Service', () => {
	beforeEach(() => {
		// Clear cache before each test
		cacheService.clearAllCache();

		// Reset all mocks
		vi.resetAllMocks();
	});

	afterEach(() => {
		vi.resetAllMocks();
	});

	describe('getStockPrice', () => {
		it('should fetch from API when cache is empty', async () => {
			// Mock API response
			const mockResponse = {
				symbol: 'AAPL',
				price: 150.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getStockPrice).mockResolvedValue(mockResponse);

			// Call the enhanced API function
			const result = await enhancedApi.getStockPrice('AAPL');

			// Verify API was called
			expect(api.getStockPrice).toHaveBeenCalledWith('AAPL', undefined);
			expect(result).toEqual(mockResponse);
		});

		it('should use cache for subsequent calls', async () => {
			// Mock API response
			const mockResponse = {
				symbol: 'AAPL',
				price: 150.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getStockPrice).mockResolvedValue(mockResponse);

			// First call should hit the API
			await enhancedApi.getStockPrice('AAPL');

			// Reset mock to verify it's not called again
			vi.mocked(api.getStockPrice).mockClear();

			// Second call should use cache
			const result = await enhancedApi.getStockPrice('AAPL');

			// Verify API was not called again
			expect(api.getStockPrice).not.toHaveBeenCalled();
			expect(result).toEqual(mockResponse);
		});

		it('should bypass cache when forceRefresh is true', async () => {
			// Mock API response
			const mockResponse1 = {
				symbol: 'AAPL',
				price: 150.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			const mockResponse2 = {
				symbol: 'AAPL',
				price: 155.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getStockPrice).mockResolvedValueOnce(mockResponse1);
			vi.mocked(api.getStockPrice).mockResolvedValueOnce(mockResponse2);

			// First call to populate cache
			await enhancedApi.getStockPrice('AAPL');

			// Second call with forceRefresh should bypass cache
			const result = await enhancedApi.getStockPrice('AAPL', { forceRefresh: true });

			// Verify API was called again with forceRefresh
			expect(api.getStockPrice).toHaveBeenCalledWith('AAPL', true);
			expect(result).toEqual(mockResponse2);
		});
	});

	describe('getCryptoPrice', () => {
		it('should fetch from API when cache is empty', async () => {
			// Mock API response
			const mockResponse = {
				symbol: 'BTC',
				price: 50000.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getCryptoPrice).mockResolvedValue(mockResponse);

			// Call the enhanced API function
			const result = await enhancedApi.getCryptoPrice('BTC');

			// Verify API was called
			expect(api.getCryptoPrice).toHaveBeenCalledWith('BTC', undefined);
			expect(result).toEqual(mockResponse);
		});

		it('should use cache for subsequent calls', async () => {
			// Mock API response
			const mockResponse = {
				symbol: 'BTC',
				price: 50000.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getCryptoPrice).mockResolvedValue(mockResponse);

			// First call should hit the API
			await enhancedApi.getCryptoPrice('BTC');

			// Reset mock to verify it's not called again
			vi.mocked(api.getCryptoPrice).mockClear();

			// Second call should use cache
			const result = await enhancedApi.getCryptoPrice('BTC');

			// Verify API was not called again
			expect(api.getCryptoPrice).not.toHaveBeenCalled();
			expect(result).toEqual(mockResponse);
		});
	});

	describe('getConversionRate', () => {
		it('should return rate of 1 when currencies are the same', async () => {
			// Call with same currencies
			const result = await enhancedApi.getConversionRate('USD', 'USD');

			// Verify API was not called
			expect(api.getConversionRate).not.toHaveBeenCalled();
			expect(result).toEqual({
				from: 'USD',
				to: 'USD',
				rate: 1,
				cached: true
			});
		});

		it('should fetch from API when cache is empty', async () => {
			// Mock API response
			const mockResponse = {
				from: 'USD',
				to: 'EUR',
				rate: 0.85,
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getConversionRate).mockResolvedValue(mockResponse);

			// Call the enhanced API function
			const result = await enhancedApi.getConversionRate('USD', 'EUR');

			// Verify API was called
			expect(api.getConversionRate).toHaveBeenCalledWith('USD', 'EUR', undefined);
			expect(result).toEqual(mockResponse);
		});
	});

	describe('convertCurrency', () => {
		it('should return same amount when currencies are the same', async () => {
			// Call with same currencies
			const result = await enhancedApi.convertCurrency('USD', 'USD', 100);

			// Verify API was not called
			expect(api.convertCurrency).not.toHaveBeenCalled();
			expect(result).toEqual({
				from: 'USD',
				to: 'USD',
				amount: 100,
				converted: 100,
				rate: 1,
				cached: true
			});
		});

		it('should fetch from API when cache is empty', async () => {
			// Mock API response
			const mockResponse = {
				from: 'USD',
				to: 'EUR',
				amount: 100,
				converted: 85,
				rate: 0.85,
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.convertCurrency).mockResolvedValue(mockResponse);

			// Call the enhanced API function
			const result = await enhancedApi.convertCurrency('USD', 'EUR', 100);

			// Verify API was called
			expect(api.convertCurrency).toHaveBeenCalledWith('USD', 'EUR', 100, undefined);
			expect(result).toEqual(mockResponse);
		});
	});

	describe('batchGetPrices', () => {
		it('should throw error when symbols and types arrays have different lengths', async () => {
			await expect(enhancedApi.batchGetPrices(['AAPL', 'MSFT'], ['stock'])).rejects.toThrow(
				'Symbols and types arrays must have the same length'
			);
		});

		it('should fetch prices for multiple assets', async () => {
			// Mock API responses
			const mockAppleResponse = {
				symbol: 'AAPL',
				price: 150.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			const mockBtcResponse = {
				symbol: 'BTC',
				price: 50000.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getStockPrice).mockResolvedValue(mockAppleResponse);
			vi.mocked(api.getCryptoPrice).mockResolvedValue(mockBtcResponse);

			// Call the batch function
			const results = await enhancedApi.batchGetPrices(['AAPL', 'BTC'], ['stock', 'crypto']);

			// Verify API calls
			expect(api.getStockPrice).toHaveBeenCalledWith('AAPL', true);
			expect(api.getCryptoPrice).toHaveBeenCalledWith('BTC', true);

			// Verify results
			expect(results).toEqual([mockAppleResponse, mockBtcResponse]);
		});

		it('should use cache for already cached assets', async () => {
			// Mock API responses
			const mockAppleResponse = {
				symbol: 'AAPL',
				price: 150.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			const mockBtcResponse = {
				symbol: 'BTC',
				price: 50000.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			vi.mocked(api.getStockPrice).mockResolvedValue(mockAppleResponse);
			vi.mocked(api.getCryptoPrice).mockResolvedValue(mockBtcResponse);

			// Pre-cache AAPL
			await enhancedApi.getStockPrice('AAPL');

			// Reset mocks
			vi.mocked(api.getStockPrice).mockClear();
			vi.mocked(api.getCryptoPrice).mockClear();

			// Call the batch function without force refresh
			const results = await enhancedApi.batchGetPrices(['AAPL', 'BTC'], ['stock', 'crypto'], {
				forceRefresh: false
			});

			// Verify only BTC was fetched from API
			expect(api.getStockPrice).not.toHaveBeenCalled();
			expect(api.getCryptoPrice).toHaveBeenCalledWith('BTC', true);

			// Verify results
			expect(results).toEqual([mockAppleResponse, mockBtcResponse]);
		});

		it('should handle API errors gracefully', async () => {
			// Mock API responses - one success, one failure
			const mockAppleResponse = {
				symbol: 'AAPL',
				price: 150.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			// Mock successful response for AAPL
			vi.mocked(api.getStockPrice).mockResolvedValue(mockAppleResponse);

			// Mock failed response for BTC
			vi.mocked(api.getCryptoPrice).mockRejectedValue(new Error('API rate limit exceeded'));

			// Call the batch function
			const results = await enhancedApi.batchGetPrices(['AAPL', 'BTC'], ['stock', 'crypto']);

			// Verify API calls were made
			expect(api.getStockPrice).toHaveBeenCalledWith('AAPL', true);
			expect(api.getCryptoPrice).toHaveBeenCalledWith('BTC', true);

			// Verify results - AAPL should have data, BTC should have error placeholder
			expect(results[0]).toEqual(mockAppleResponse);
			expect(results[1]).toMatchObject({
				symbol: 'BTC',
				price: 0,
				currency: 'USD',
				cached: false,
				source: 'error'
			});
		});

		it('should use stale cache data when API fails', async () => {
			// Create cached data for BTC
			const cachedBtcResponse = {
				symbol: 'BTC',
				price: 48000.0,
				currency: 'USD',
				cached: true,
				fetched_at: new Date(Date.now() - 3600000).toISOString() // 1 hour old
			};

			// Set cache
			cacheService.set('crypto_price_BTC', cachedBtcResponse);

			// Mock API responses
			const mockAppleResponse = {
				symbol: 'AAPL',
				price: 150.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			// Mock successful response for AAPL
			vi.mocked(api.getStockPrice).mockResolvedValue(mockAppleResponse);

			// Mock failed response for BTC
			vi.mocked(api.getCryptoPrice).mockRejectedValue(new Error('API rate limit exceeded'));

			// Call the batch function with force refresh to trigger API calls
			const results = await enhancedApi.batchGetPrices(['AAPL', 'BTC'], ['stock', 'crypto'], {
				forceRefresh: true
			});

			// Verify API calls were made
			expect(api.getStockPrice).toHaveBeenCalledWith('AAPL', true);
			expect(api.getCryptoPrice).toHaveBeenCalledWith('BTC', true);

			// Verify results - AAPL should have fresh data, BTC should use cached data
			expect(results[0]).toEqual(mockAppleResponse);
			expect(results[1]).toMatchObject({
				symbol: 'BTC',
				price: 48000.0,
				currency: 'USD',
				cached: true
			});
		});

		it('should optimize API calls by grouping by asset type', async () => {
			// Mock API responses
			const mockStockResponse = {
				symbol: 'MOCK',
				price: 100.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			const mockCryptoResponse = {
				symbol: 'MOCK',
				price: 1000.0,
				currency: 'USD',
				cached: false,
				fetched_at: new Date().toISOString()
			};

			// Setup mocks to return different responses based on symbol
			vi.mocked(api.getStockPrice).mockImplementation((symbol) => {
				return Promise.resolve({
					...mockStockResponse,
					symbol
				});
			});

			vi.mocked(api.getCryptoPrice).mockImplementation((symbol) => {
				return Promise.resolve({
					...mockCryptoResponse,
					symbol
				});
			});

			// Call the batch function with multiple assets of each type
			const results = await enhancedApi.batchGetPrices(
				['AAPL', 'MSFT', 'GOOG', 'BTC', 'ETH', 'XRP'],
				['stock', 'stock', 'stock', 'crypto', 'crypto', 'crypto']
			);

			// Verify API calls were made for each symbol
			expect(api.getStockPrice).toHaveBeenCalledWith('AAPL', true);
			expect(api.getStockPrice).toHaveBeenCalledWith('MSFT', true);
			expect(api.getStockPrice).toHaveBeenCalledWith('GOOG', true);
			expect(api.getCryptoPrice).toHaveBeenCalledWith('BTC', true);
			expect(api.getCryptoPrice).toHaveBeenCalledWith('ETH', true);
			expect(api.getCryptoPrice).toHaveBeenCalledWith('XRP', true);

			// Verify results contain all expected items
			expect(results.length).toBe(6);
			expect(results[0].symbol).toBe('AAPL');
			expect(results[1].symbol).toBe('MSFT');
			expect(results[2].symbol).toBe('GOOG');
			expect(results[3].symbol).toBe('BTC');
			expect(results[4].symbol).toBe('ETH');
			expect(results[5].symbol).toBe('XRP');
		});
	});

	describe('clearPriceCache', () => {
		it('should clear both backend and frontend cache', async () => {
			// Mock API response
			const mockResponse = { message: 'Cache cleared' };
			vi.mocked(api.clearPriceCache).mockResolvedValue(mockResponse);

			// Pre-populate cache
			cacheService.set('stock_price_AAPL', { symbol: 'AAPL', price: 150 });
			cacheService.set('crypto_price_BTC', { symbol: 'BTC', price: 50000 });

			// Verify cache has items
			expect(cacheService.has('stock_price_AAPL')).toBe(true);
			expect(cacheService.has('crypto_price_BTC')).toBe(true);

			// Clear cache
			const result = await enhancedApi.clearPriceCache();

			// Verify backend API was called
			expect(api.clearPriceCache).toHaveBeenCalled();

			// Verify frontend cache was cleared
			expect(cacheService.has('stock_price_AAPL')).toBe(false);
			expect(cacheService.has('crypto_price_BTC')).toBe(false);

			// Verify result
			expect(result).toEqual(mockResponse);
		});
	});

	describe('clearConversionCache', () => {
		it('should clear both backend and frontend cache', async () => {
			// Mock API response
			const mockResponse = { message: 'Cache cleared' };
			vi.mocked(api.clearConversionCache).mockResolvedValue(mockResponse);

			// Pre-populate cache
			cacheService.set('conversion_rate_USD_EUR', { from: 'USD', to: 'EUR', rate: 0.85 });

			// Verify cache has items
			expect(cacheService.has('conversion_rate_USD_EUR')).toBe(true);

			// Clear cache
			const result = await enhancedApi.clearConversionCache();

			// Verify backend API was called
			expect(api.clearConversionCache).toHaveBeenCalled();

			// Verify frontend cache was cleared
			expect(cacheService.has('conversion_rate_USD_EUR')).toBe(false);

			// Verify result
			expect(result).toEqual(mockResponse);
		});
	});

	describe('getAssetCacheInfo', () => {
		it('should return cache info for an asset', async () => {
			// Pre-populate cache
			cacheService.set('stock_price_AAPL', { symbol: 'AAPL', price: 150 });

			// Get cache info
			const info = enhancedApi.getAssetCacheInfo('AAPL', 'stock');

			// Verify info
			expect(info.isCached).toBe(true);
			expect(info.isValid).toBe(true);
			expect(typeof info.age).toBe('number');
			expect(typeof info.formattedAge).toBe('string');
			expect(typeof info.timeUntilExpiration).toBe('number');
			expect(typeof info.formattedExpiration).toBe('string');
			expect(typeof info.hitRate).toBe('number');
		});

		it('should return cache info for non-cached asset', () => {
			// Get cache info for non-cached asset
			const info = enhancedApi.getAssetCacheInfo('MSFT', 'stock');

			// Verify info
			expect(info.isCached).toBe(false);
			expect(info.isValid).toBe(false);
			expect(info.age).toBe(-1);
			expect(info.formattedAge).toBe('Not cached');
			expect(info.timeUntilExpiration).toBe(-1);
			expect(info.formattedExpiration).toBe('Expired');
		});
	});
});

describe('batchConvertCurrency', () => {
	beforeEach(() => {
		// Clear cache before each test
		cacheService.clearAllCache();

		// Reset all mocks
		vi.resetAllMocks();
	});

	afterEach(() => {
		vi.resetAllMocks();
	});

	it('should throw error when arrays have different lengths', async () => {
		await expect(
			enhancedApi.batchConvertCurrency([100, 200], ['USD', 'EUR'], ['EUR'])
		).rejects.toThrow('Amounts, fromCurrencies, and toCurrencies arrays must have the same length');
	});

	it('should skip conversion when currencies are the same', async () => {
		const results = await enhancedApi.batchConvertCurrency(
			[100, 200],
			['USD', 'EUR'],
			['USD', 'EUR']
		);

		// Verify API was not called
		expect(api.convertCurrency).not.toHaveBeenCalled();

		// Verify results
		expect(results).toEqual([
			{
				from: 'USD',
				to: 'USD',
				amount: 100,
				converted: 100,
				rate: 1,
				cached: true
			},
			{
				from: 'EUR',
				to: 'EUR',
				amount: 200,
				converted: 200,
				rate: 1,
				cached: true
			}
		]);
	});

	it('should fetch conversions for multiple currencies', async () => {
		// Mock API responses
		const mockUsdEurResponse = {
			from: 'USD',
			to: 'EUR',
			amount: 100,
			converted: 85,
			rate: 0.85,
			cached: false,
			fetched_at: new Date().toISOString()
		};

		const mockEurJpyResponse = {
			from: 'EUR',
			to: 'JPY',
			amount: 200,
			converted: 26000,
			rate: 130,
			cached: false,
			fetched_at: new Date().toISOString()
		};

		vi.mocked(api.convertCurrency).mockImplementation((from, to, amount) => {
			if (from === 'USD' && to === 'EUR') {
				return Promise.resolve({
					...mockUsdEurResponse,
					amount,
					converted: amount * 0.85
				});
			} else if (from === 'EUR' && to === 'JPY') {
				return Promise.resolve({
					...mockEurJpyResponse,
					amount,
					converted: amount * 130
				});
			}
			return Promise.reject(new Error('Unexpected currency pair'));
		});

		// Call the batch function
		const results = await enhancedApi.batchConvertCurrency(
			[100, 200],
			['USD', 'EUR'],
			['EUR', 'JPY']
		);

		// Verify results
		expect(results).toEqual([mockUsdEurResponse, mockEurJpyResponse]);
	});

	it('should use cache for already cached conversions', async () => {
		// Mock API responses
		const mockUsdEurResponse = {
			from: 'USD',
			to: 'EUR',
			amount: 100,
			converted: 85,
			rate: 0.85,
			cached: true,
			fetched_at: new Date().toISOString()
		};

		const mockEurJpyResponse = {
			from: 'EUR',
			to: 'JPY',
			amount: 200,
			converted: 26000,
			rate: 130,
			cached: false,
			fetched_at: new Date().toISOString()
		};

		// Set up the mock implementation
		vi.mocked(api.convertCurrency).mockImplementation((from, to, amount) => {
			if (from === 'EUR' && to === 'JPY') {
				return Promise.resolve({
					...mockEurJpyResponse,
					amount,
					converted: amount * 130
				});
			}
			return Promise.reject(new Error('Unexpected currency pair'));
		});

		// Pre-cache USD to EUR conversion
		cacheService.set('conversion_USD_EUR_100', mockUsdEurResponse);

		// Call the batch function
		const results = await enhancedApi.batchConvertCurrency(
			[100, 200],
			['USD', 'EUR'],
			['EUR', 'JPY'],
			{ forceRefresh: false }
		);

		// Verify results - first should be from cache, second from API
		expect(results[0]).toEqual(mockUsdEurResponse);
		expect(results[1]).toEqual(mockEurJpyResponse);
	});

	it('should handle API errors gracefully', async () => {
		// Mock API responses - one success, one failure
		const mockUsdEurResponse = {
			from: 'USD',
			to: 'EUR',
			amount: 100,
			converted: 85,
			rate: 0.85,
			cached: false,
			fetched_at: new Date().toISOString()
		};

		// Mock successful response for USD to EUR
		vi.mocked(api.convertCurrency).mockImplementation((from, to, amount) => {
			if (from === 'USD' && to === 'EUR') {
				return Promise.resolve({
					...mockUsdEurResponse,
					amount,
					converted: amount * 0.85
				});
			}
			return Promise.reject(new Error('API rate limit exceeded'));
		});

		// Call the batch function
		const results = await enhancedApi.batchConvertCurrency(
			[100, 200],
			['USD', 'EUR'],
			['EUR', 'JPY']
		);

		// Verify results - USD to EUR should have data, EUR to JPY should have error fallback
		expect(results[0]).toEqual(mockUsdEurResponse);
		expect(results[1]).toMatchObject({
			from: 'EUR',
			to: 'JPY',
			amount: 200,
			source: 'error'
		});
	});

	it('should use stale cache data when API fails', async () => {
		// Create cached data for EUR to JPY
		const cachedEurJpyResponse = {
			from: 'EUR',
			to: 'JPY',
			amount: 200,
			converted: 26000,
			rate: 130,
			cached: true,
			fetched_at: new Date(Date.now() - 3600000).toISOString() // 1 hour old
		};

		// Set cache
		cacheService.set('conversion_EUR_JPY_200', cachedEurJpyResponse);

		// Mock API responses
		const mockUsdEurResponse = {
			from: 'USD',
			to: 'EUR',
			amount: 100,
			converted: 85,
			rate: 0.85,
			cached: false,
			fetched_at: new Date().toISOString()
		};

		// Mock successful response for USD to EUR
		vi.mocked(api.convertCurrency).mockImplementation((from, to, amount) => {
			if (from === 'USD' && to === 'EUR') {
				return Promise.resolve({
					...mockUsdEurResponse,
					amount,
					converted: amount * 0.85
				});
			}
			return Promise.reject(new Error('API rate limit exceeded'));
		});

		// Call the batch function with force refresh to trigger API calls
		const results = await enhancedApi.batchConvertCurrency(
			[100, 200],
			['USD', 'EUR'],
			['EUR', 'JPY'],
			{ forceRefresh: true }
		);

		// Verify results - USD to EUR should have fresh data, EUR to JPY should use cached data
		expect(results[0]).toEqual(mockUsdEurResponse);
		expect(results[1]).toMatchObject({
			from: 'EUR',
			to: 'JPY',
			amount: 200,
			converted: 26000,
			rate: 130,
			cached: true
		});
	});
});
