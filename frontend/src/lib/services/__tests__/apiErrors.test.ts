/**
 * Error messages shown by the add/edit holding form.
 * Response bodies match what the backend's error handlers return.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAsset, deleteAsset, responseErrorMessage, updateAsset } from '../api';

function jsonResponse(status: number, body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

function validationFailed(errors: { loc: string[]; msg: string; type: string }[]) {
	return jsonResponse(422, {
		error: true,
		message: 'Request validation failed',
		category: 'validation_error',
		status_code: 422,
		details: { validation_errors: errors }
	});
}

describe('responseErrorMessage', () => {
	it('shows holding rule messages from create', async () => {
		const response = validationFailed([
			{
				loc: ['body'],
				msg: 'Value error, negative quantity is only allowed for cash; purchase price must not be negative',
				type: 'value_error'
			}
		]);

		expect(await responseErrorMessage(response, 'Failed')).toBe(
			'Negative quantity is only allowed for cash; purchase price must not be negative'
		);
	});

	it('shows holding rule messages from update', async () => {
		const response = validationFailed([
			{
				loc: ['body', 'quantity'],
				msg: 'negative quantity is only allowed for cash',
				type: 'value_error'
			},
			{
				loc: ['body', 'purchase_price'],
				msg: 'purchase price must not be negative',
				type: 'value_error'
			}
		]);

		expect(await responseErrorMessage(response, 'Failed')).toBe(
			'Negative quantity is only allowed for cash; purchase price must not be negative'
		);
	});

	it('names the field when the message does not', async () => {
		const response = validationFailed([
			{
				loc: ['body', 'type'],
				msg: "Input should be 'cash', 'stock', 'crypto' or 'derivative'",
				type: 'enum'
			}
		]);

		expect(await responseErrorMessage(response, 'Failed')).toBe(
			"Type: Input should be 'cash', 'stock', 'crypto' or 'derivative'"
		);
	});

	it('uses the error message for other errors', async () => {
		const response = jsonResponse(404, {
			error: true,
			message: 'Asset not found',
			category: 'not_found_error',
			status_code: 404
		});

		expect(await responseErrorMessage(response, 'Failed')).toBe('Asset not found');
	});

	it('uses FastAPI detail strings', async () => {
		const response = jsonResponse(404, { detail: 'Asset not found' });

		expect(await responseErrorMessage(response, 'Failed')).toBe('Asset not found');
	});

	it('falls back when the body is not JSON', async () => {
		const response = new Response('<html>Bad gateway</html>', { status: 502 });

		expect(await responseErrorMessage(response, 'Failed to create asset')).toBe(
			'Failed to create asset'
		);
	});

	it('falls back when the body has no usable message', async () => {
		const response = jsonResponse(500, { error: true });

		expect(await responseErrorMessage(response, 'Failed to update asset')).toBe(
			'Failed to update asset'
		);
	});
});

describe('holding requests', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	function stubFetch(response: Response) {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
	}

	it('createAsset throws the rule message', async () => {
		stubFetch(
			validationFailed([
				{
					loc: ['body'],
					msg: 'Value error, negative quantity is only allowed for cash',
					type: 'value_error'
				}
			])
		);

		await expect(
			createAsset({ type: 'stock', name: 'Broker', quantity: -1 } as never)
		).rejects.toThrow('Negative quantity is only allowed for cash');
	});

	it('updateAsset throws the rule message', async () => {
		stubFetch(
			validationFailed([
				{
					loc: ['body', 'purchase_price'],
					msg: 'purchase price must not be negative',
					type: 'value_error'
				}
			])
		);

		await expect(updateAsset(1, { purchase_price: -1 })).rejects.toThrow(
			'Purchase price must not be negative'
		);
	});

	it('deleteAsset throws the server message', async () => {
		stubFetch(jsonResponse(404, { error: true, message: 'Asset not found' }));

		await expect(deleteAsset(999)).rejects.toThrow('Asset not found');
	});
});
