import { writable, derived, get } from 'svelte/store';
import type { AuthState, SessionData } from '$lib/types';
import { authApiService } from '$lib/services/authApi';
import { devLog } from '$lib/utils/logger';
import { browser } from '$app/environment';

// Session storage key
const SESSION_STORAGE_KEY = 'cointainr_auth_session';

// Session validation interval (5 minutes)
const SESSION_VALIDATION_INTERVAL = 5 * 60 * 1000;

// Initial auth state
const initialAuthState: AuthState = {
	isAuthenticated: false,
	isLoading: false,
	error: null,
	username: '',
	demoMode: false,
	expiresAt: null,
	sessionToken: null
};

// Create the writable store
const authStore = writable<AuthState>(initialAuthState);

// Session validation timer
let sessionValidationTimer: NodeJS.Timeout | null = null;

/**
 * Session persistence utilities with security considerations
 */
class SessionManager {
	/**
	 * Save session data to browser storage
	 */
	saveSession(sessionData: SessionData): void {
		if (!browser) return;

		try {
			// Use sessionStorage for security - data is cleared when browser closes
			sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionData));
			devLog.info('Session saved to storage');
		} catch (error) {
			console.error('Failed to save session to storage:', error);
		}
	}

	/**
	 * Load session data from browser storage
	 */
	loadSession(): SessionData | null {
		if (!browser) return null;

		try {
			const sessionJson = sessionStorage.getItem(SESSION_STORAGE_KEY);
			if (!sessionJson) return null;

			const sessionData: SessionData = JSON.parse(sessionJson);

			// Validate session data structure
			if (!this.isValidSessionData(sessionData)) {
				devLog.warn('Invalid session data found, clearing storage');
				this.clearSession();
				return null;
			}

			// Check if session has expired
			if (this.isSessionExpired(sessionData)) {
				devLog.warn('Session expired, clearing storage');
				this.clearSession();
				return null;
			}

			devLog.info('Session loaded from storage', { username: sessionData.username });
			return sessionData;
		} catch (error) {
			console.error('Failed to load session from storage:', error);
			this.clearSession();
			return null;
		}
	}

	/**
	 * Clear session data from browser storage
	 */
	clearSession(): void {
		if (!browser) return;

		try {
			sessionStorage.removeItem(SESSION_STORAGE_KEY);
			devLog.info('Session cleared from storage');
		} catch (error) {
			console.error('Failed to clear session from storage:', error);
		}
	}

	/**
	 * Validate session data structure
	 */
	private isValidSessionData(data: any): data is SessionData {
		return (
			data &&
			typeof data.sessionToken === 'string' &&
			typeof data.username === 'string' &&
			typeof data.demoMode === 'boolean' &&
			typeof data.expiresAt === 'string' &&
			typeof data.lastValidated === 'string'
		);
	}

	/**
	 * Check if session has expired
	 */
	private isSessionExpired(sessionData: SessionData): boolean {
		const expiresAt = new Date(sessionData.expiresAt);
		const now = new Date();
		return now >= expiresAt;
	}
}

const sessionManager = new SessionManager();

/**
 * Authentication store actions
 */
export const authActions = {
	/**
	 * Attempt to log in with provided credentials
	 */
	async login(username: string, password: string): Promise<boolean> {
		authStore.update((state) => ({ ...state, isLoading: true, error: null }));

		try {
			const response = await authApiService.login(username, password);

			if (response.success) {
				const sessionData: SessionData = {
					sessionToken: '', // Don't store token - backend uses HTTP-only cookie
					username: response.username,
					demoMode: response.demo_mode,
					expiresAt: response.expires_at,
					lastValidated: new Date().toISOString()
				};

				// Save session to storage (without token for security)
				sessionManager.saveSession(sessionData);

				// Update store state
				authStore.set({
					isAuthenticated: true,
					isLoading: false,
					error: null,
					username: response.username,
					demoMode: response.demo_mode,
					expiresAt: response.expires_at,
					sessionToken: '' // Don't store token - backend uses HTTP-only cookie
				});

				// Start session validation timer
				startSessionValidation();

				devLog.info('Login successful', {
					username: response.username,
					demoMode: response.demo_mode
				});
				return true;
			} else {
				throw new Error('Login failed');
			}
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : 'Login failed';
			authStore.update((state) => ({
				...state,
				isLoading: false,
				error: errorMessage
			}));
			devLog.error('Login failed', { error: errorMessage });
			return false;
		}
	},

	/**
	 * Log out the current user
	 */
	async logout(): Promise<void> {
		authStore.update((state) => ({ ...state, isLoading: true }));

		try {
			// Call logout API
			await authApiService.logout();
		} catch (error) {
			// Log error but continue with logout process
			console.error('Logout API call failed:', error);
		}

		// Clear session regardless of API call result
		sessionManager.clearSession();
		stopSessionValidation();

		// Reset store state
		authStore.set(initialAuthState);

		devLog.info('Logout completed');
	},

	/**
	 * Check authentication status with the server
	 */
	async checkAuthStatus(): Promise<boolean> {
		try {
			const response = await authApiService.checkAuthStatus();

			if (response.authenticated) {
				// Update session data for UI purposes (no token stored)
				const sessionData: SessionData = {
					sessionToken: '', // Never store token - backend uses HTTP-only cookie
					username: response.username,
					demoMode: response.demo_mode,
					expiresAt: response.expires_at,
					lastValidated: new Date().toISOString()
				};

				// Save session data (for UI state, not authentication)
				sessionManager.saveSession(sessionData);

				// Update store state
				authStore.update((state) => ({
					...state,
					isAuthenticated: true,
					username: response.username,
					demoMode: response.demo_mode,
					expiresAt: response.expires_at,
					sessionToken: '', // Don't store token in memory
					error: null
				}));

				return true;
			} else {
				// Not authenticated, clear session
				sessionManager.clearSession();
				authStore.update((state) => ({
					...state,
					isAuthenticated: false,
					username: '',
					demoMode: false,
					expiresAt: null,
					sessionToken: null
				}));

				return false;
			}
		} catch (error) {
			console.error('Auth status check failed:', error);
			return false;
		}
	},

	/**
	 * Initialize authentication state from stored session
	 */
	async initializeAuth(): Promise<void> {
		if (!browser) return;

		authStore.update((state) => ({ ...state, isLoading: true }));

		try {
			// Always check with server using HTTP-only cookie
			// Don't rely on sessionStorage since backend uses HTTP-only cookies
			const isValid = await this.checkAuthStatus();

			if (isValid) {
				// Session is valid, start validation timer
				startSessionValidation();
				devLog.info('Authentication initialized from HTTP-only cookie');
			} else {
				// No valid session, clear any stored data
				sessionManager.clearSession();
				authStore.set(initialAuthState);
			}
		} catch (error) {
			console.error('Failed to initialize auth:', error);
			sessionManager.clearSession();
			authStore.set(initialAuthState);
		}
	},

	/**
	 * Clear any authentication errors
	 */
	clearError(): void {
		authStore.update((state) => ({ ...state, error: null }));
	}
};

/**
 * Start automatic session validation
 */
function startSessionValidation(): void {
	// Clear existing timer
	stopSessionValidation();

	// Set up new validation timer
	sessionValidationTimer = setInterval(async () => {
		const currentState = get(authStore);

		// Only validate if currently authenticated
		if (currentState.isAuthenticated) {
			const isValid = await authActions.checkAuthStatus();

			if (!isValid) {
				// Session invalid, logout
				await authActions.logout();
				devLog.warn('Session validation failed, user logged out');
			} else {
				devLog.info('Session validation successful');
			}
		}
	}, SESSION_VALIDATION_INTERVAL);

	devLog.info('Session validation timer started');
}

/**
 * Stop automatic session validation
 */
function stopSessionValidation(): void {
	if (sessionValidationTimer) {
		clearInterval(sessionValidationTimer);
		sessionValidationTimer = null;
		devLog.info('Session validation timer stopped');
	}
}

// Derived stores for convenient access to specific auth state
export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);
export const isLoading = derived(authStore, ($auth) => $auth.isLoading);
export const authError = derived(authStore, ($auth) => $auth.error);
export const currentUser = derived(authStore, ($auth) => ({
	username: $auth.username,
	demoMode: $auth.demoMode,
	expiresAt: $auth.expiresAt
}));

// Export the main store and actions
export { authStore };
export default authStore;
