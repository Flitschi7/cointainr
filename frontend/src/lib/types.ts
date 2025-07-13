/**
 * Enum for supported asset types.
 */
export type AssetType = 'cash' | 'stock' | 'crypto';

/**
 * Asset interface representing a financial asset.
 */
export interface Asset {
	id: number;
	type: AssetType;
	name: string;
	quantity: number;
	symbol: string | null;
	currency: string | null;
	purchase_price: number | null;
	buy_currency: string | null;
}
