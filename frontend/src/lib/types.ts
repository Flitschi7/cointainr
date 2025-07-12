export interface Asset {
	id: number;
	type: 'cash' | 'stock' | 'crypto';
	name: string;
	quantity: number;
	symbol: string | null;
	currency: string | null;
	purchase_price: number | null;
}
