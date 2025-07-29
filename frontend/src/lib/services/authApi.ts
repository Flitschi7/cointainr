import { devLog } from '$lib/utils/logger';

// Environment-aware API base URL configuration (reusing pattern from api.ts)
function getApiBaseUrl(): string {
	if (typeof window !== 'undefined') {
		if (
			window.location.origin.includes('localhost:8893') ||
			window.location.origin.includes('127.0.0.1:8893') ||
			import.meta.env.PROD
		) {
			return '/api/v1';
		}
	}
	return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
}

const API_BASE_URL = getApiBaseUrl();

// Authentication API interfaces
export interface LoginRequest {
	username: string;
	password: string;
}

export interface LoginResponse {
	success: boolean;
	session_token: string;
	expires_at: string;
	demo_mode: boolean;
	username: string;
}

export interface AuthStatusResponse {
	authenticated: boolean;
	username: string;
	demo_mode: boolean;
	expires_at: string;
}

export interface LogoutResponse {
	success: boolean;
	message: string;
}

/**
 * Authentication API service for handling login, logout, and session management
 */
export class AuthApiService {
	/**
	 * Attempt to log in with provided credentials
	 */
	async login(username: string, password: string): Promise<LoginResponse> {
		try {
			const response = await fetch(`${API_BASE_URL}/auth/login`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ username, password }),
				credentials: 'include' // Include cookies for session management
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || 'Login failed');
			}

			const data = await response.json();
			devLog.info('Login successful', { username, demo_mode: data.demo_mode });
			return data;
		} catch (error) {
			devLog.error('Login failed', {
				username,
				error: error instanceof Error ? error.message : String(error)
			});
			throw error;
		}
	}

	/**
	 * Log out the current user
	 */
	async logout(): Promise<LogoutResponse> {
		try {
			const response = await fetch(`${API_BASE_URL}/auth/logout`, {
				method: 'POST',
				credentials: 'include'
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || 'Logout failed');
			}

			const data = await response.json();
			devLog.info('Logout successful');
			return data;
		} catch (error) {
			devLog.error('Logout failed', {
				error: error instanceof Error ? error.message : String(error)
			});
			throw error;
		}
	}

	/**
	 * Check the current authentication status
	 */
	async checkAuthStatus(customFetch?: typeof fetch): Promise<AuthStatusResponse> {
		try {
			const fetchFn = customFetch || fetch;
			const response = await fetchFn(`${API_BASE_URL}/auth/status`, {
				method: 'GET',
				credentials: 'include'
			});

			if (!response.ok) {
				// If status check fails, user is not authenticated
				return {
					authenticated: false,
					username: '',
					demo_mode: false,
					expires_at: ''
				};
			}

			const data = await response.json();
			devLog.info('Auth status checked', {
				authenticated: data.authenticated,
				username: data.username
			});
			return data;
		} catch (error) {
			devLog.error('Auth status check failed', {
				error: error instanceof Error ? error.message : String(error)
			});
			// Return unauthenticated state on error
			return {
				authenticated: false,
				username: '',
				demo_mode: false,
				expires_at: ''
			};
		}
	}
}

// Export singleton instance
export const authApiService = new AuthApiService();
