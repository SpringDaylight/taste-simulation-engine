/**
 * HTTP client configuration
 */

// API Base URL - 환경변수로 관리 가능
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const ACCESS_TOKEN_KEY = 'mw_access_token';
let hasForcedLogout = false;

function notifyAuthChange() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event("mw_auth_change"));
}

export function setAccessToken(token: string | null) {
  if (!token) {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem("mw_user_pk");
    localStorage.removeItem("mw_user_id");
    notifyAuthChange();
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
  notifyAuthChange();
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function extractErrorDetail(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object' && 'msg' in item) {
            const msg = (item as { msg?: unknown }).msg;
            if (typeof msg === 'string') return msg;
          }
          return '';
        })
        .filter(Boolean);
      if (messages.length) return messages.join(', ');
    }
  }

  try {
    return JSON.stringify(payload) || fallback;
  } catch {
    return fallback;
  }
}

/**
 * HTTP request wrapper with error handling
 */
async function tryRefreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      setAccessToken(null);
      return false;
    }
    const payload = await response.json();
    if (payload && payload.access_token) {
      setAccessToken(payload.access_token);
      return true;
    }
    setAccessToken(null);
    return false;
  } catch (error) {
    console.error('Failed to refresh token:', error);
    setAccessToken(null);
    return false;
  }
}

function forceLogout() {
  if (hasForcedLogout) return;
  hasForcedLogout = true;
  setAccessToken(null);
  if (typeof window !== "undefined") {
    window.location.replace("/");
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  allowRetry = true
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const accessToken = getAccessToken();
  const config: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
    credentials: 'include',
  };

  try {
    const response = await fetch(url, config);

    if (
      response.status === 401 &&
      allowRetry &&
      !endpoint.startsWith('/api/auth/login') &&
      !endpoint.startsWith('/api/auth/refresh') &&
      !endpoint.startsWith('/api/auth/signup')
    ) {
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        return request<T>(endpoint, options, false);
      }
      forceLogout();
    }

    if (!response.ok) {
      const fallbackMessage = `HTTP ${response.status}: ${response.statusText}`;
      let payload: unknown = null;

      try {
        payload = await response.json();
      } catch {
        try {
          payload = await response.text();
        } catch {
          payload = null;
        }
      }

      const error = new Error(extractErrorDetail(payload, fallbackMessage));
      (error as { status?: number; endpoint?: string }).status = response.status;
      (error as { status?: number; endpoint?: string }).endpoint = endpoint;
      throw error;
    }

    return await response.json();
  } catch (error) {
    const status = (error as { status?: number }).status;
    const errorEndpoint =
      (error as { endpoint?: string }).endpoint ?? endpoint;
    const message =
      error instanceof Error ? error.message.toLowerCase() : "";
    const isUserPreferenceNotFound =
      status === 404 &&
      errorEndpoint.startsWith("/api/user-preferences/") &&
      message.includes("not found");
    if (!isUserPreferenceNotFound) {
      console.error('API Request Error:', error);
    }
    throw error;
  }
}

/**
 * GET request
 */
export function get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
  const queryString = params
    ? '?' + new URLSearchParams(
        Object.entries(params)
          .filter(([_, value]) => value !== undefined && value !== null)
          .map(([key, value]) => [key, String(value)])
      ).toString()
    : '';

  return request<T>(`${endpoint}${queryString}`, {
    method: 'GET',
  });
}

/**
 * POST request
 */
export function post<T>(endpoint: string, data?: any, params?: Record<string, any>): Promise<T> {
  const queryString = params
    ? '?' + new URLSearchParams(
        Object.entries(params)
          .filter(([_, value]) => value !== undefined && value !== null)
          .map(([key, value]) => [key, String(value)])
      ).toString()
    : '';

  return request<T>(`${endpoint}${queryString}`, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * PUT request
 */
export function put<T>(endpoint: string, data?: any): Promise<T> {
  return request<T>(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * DELETE request
 */
export function del<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, {
    method: 'DELETE',
  });
}
