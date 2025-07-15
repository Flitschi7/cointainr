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

export function formatPercentage(value: number, decimals: number = 2): string {
	const formattedNumber = formatNumber(Math.abs(value), decimals);
	const sign = value >= 0 ? '+' : '-';
	return `${sign}${formattedNumber}%`;
}

export function formatValue(value: number, decimals: number = 2): string {
	return formatNumber(value, decimals);
}
