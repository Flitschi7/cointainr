import { describe, expect, it } from 'vitest';
import { formatCurrency, formatQuantity, formatUnitPrice } from '../numberFormat';

describe('formatQuantity', () => {
	it.each([
		[0.00512, '0,00512'],
		[10, '10'],
		[0.1, '0,1'],
		[1234.5, '1.234,5'],
		[0.123456789, '0,12345679'],
		[0, '0'],
		[-250.75, '-250,75']
	])('shows %s as %s', (value, expected) => {
		expect(formatQuantity(value)).toBe(expected);
	});
});

describe('formatUnitPrice', () => {
	it.each([
		[0.0004, 'USD', '0,0004 USD'],
		[0.000123456, 'USD', '0,0001235 USD'],
		[0.12345, 'EUR', '0,1235 EUR'],
		[0.5, 'EUR', '0,50 EUR'],
		[0, 'EUR', '0,00 EUR'],
		[1, 'EUR', '1,00 EUR'],
		[60000, 'USD', '60.000,00 USD'],
		[-0.0004, 'USD', '-0,0004 USD']
	])('shows %s %s as %s', (value, currency, expected) => {
		expect(formatUnitPrice(value, currency)).toBe(expected);
	});
});

describe('formatCurrency', () => {
	it('keeps money amounts at two decimals', () => {
		expect(formatCurrency(0.0004, 'USD')).toBe('0,00 USD');
		expect(formatCurrency(1234.567, 'EUR')).toBe('1.234,57 EUR');
	});
});
