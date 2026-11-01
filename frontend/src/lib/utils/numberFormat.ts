/**
 * Consistent number formatting utilities for the application
 * Uses German/European format: . for thousands, , for decimals
 */

export function formatNumber(value: number, decimals: number = 2): string {
	return new Intl.NumberFormat('de-DE', {
		minimumFractionDigits: decimals,
		maximumFractionDigits: decimals
	}).format(value);
}

export function formatCurrency(
	value: number,
	currency: string = 'EUR',
	decimals: number = 2
): string {
	const formattedNumber = formatNumber(Math.abs(value), decimals);
	const sign = value >= 0 ? '' : '-';
	return `${sign}${formattedNumber} ${currency}`;
}

/**
 * Holding quantity: up to 8 decimals (satoshi precision), no trailing zeros.
 */
export function formatQuantity(value: number): string {
	return new Intl.NumberFormat('de-DE', {
		minimumFractionDigits: 0,
		maximumFractionDigits: 8
	}).format(value);
}

/**
 * Price per unit: money precision from 1 upwards; below 1, enough decimals to
 * show four significant digits, so small quotes do not round to zero.
 */
export function formatUnitPrice(value: number, currency: string = 'EUR'): string {
	const magnitude = Math.abs(value);
	if (magnitude === 0 || magnitude >= 1) return formatCurrency(value, currency);
	const decimals = Math.min(10, Math.max(2, Math.ceil(-Math.log10(magnitude)) + 3));
	const formattedNumber = new Intl.NumberFormat('de-DE', {
		minimumFractionDigits: 2,
		maximumFractionDigits: decimals
	}).format(magnitude);
	const sign = value >= 0 ? '' : '-';
	return `${sign}${formattedNumber} ${currency}`;
}

export function formatPercentage(value: number, decimals: number = 2): string {
	const formattedNumber = formatNumber(Math.abs(value), decimals);
	const sign = value >= 0 ? '+' : '-';
	return `${sign}${formattedNumber}%`;
}

export function formatValue(value: number, decimals: number = 2): string {
	return formatNumber(value, decimals);
}
