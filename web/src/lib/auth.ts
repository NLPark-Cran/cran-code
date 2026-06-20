const AUTH_TOKEN_KEY = "cran_auth_token";
const AUTH_TOKEN_TIMESTAMP_KEY = "cran_auth_token_ts";
const AUTH_TOKEN_PARAM = "token";
const TOKEN_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

function _looksLikeJwt(token: string): boolean {
  return token.split(".").length === 3;
}

function _isJwtExpired(token: string): boolean {
  try {
    const payloadBase64 = token.split(".")[1];
    if (!payloadBase64) return true;
    const payload = JSON.parse(atob(payloadBase64));
    if (!payload.exp) return false;
    // Add a small buffer (30s) to avoid edge cases
    return Date.now() >= (payload.exp * 1000) - 30000;
  } catch {
    return true;
  }
}

function _redirectToLogin(): void {
  if (typeof window === "undefined") return;
  // Avoid redirect loops
  if (window.location.pathname === "/login") return;
  window.location.href = "/login";
}

export function getAuthToken(): string | null {
  const v1Token = localStorage.getItem(AUTH_TOKEN_KEY);
  const v2Token = localStorage.getItem("cran_v2_auth_token");
  // Prefer v2 JWT if both exist; v1 token is usually a short random string
  if (v2Token && _looksLikeJwt(v2Token)) {
    if (_isJwtExpired(v2Token)) {
      clearAuthToken();
      _redirectToLogin();
      return null;
    }
    return v2Token;
  }
  if (v1Token) {
    // Check if token has expired
    const timestamp = localStorage.getItem(AUTH_TOKEN_TIMESTAMP_KEY);
    if (timestamp) {
      const storedAt = parseInt(timestamp, 10);
      if (Number.isNaN(storedAt)) {
        clearAuthToken();
        return null;
      }
      const age = Date.now() - storedAt;
      if (age > TOKEN_EXPIRY_MS) {
        clearAuthToken();
        return null;
      }
    }
    return v1Token;
  }
  return v2Token || null;
}

export function setAuthToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_TOKEN_TIMESTAMP_KEY, Date.now().toString());
}

export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_TOKEN_TIMESTAMP_KEY);
  localStorage.removeItem("cran_v2_auth_token");
  localStorage.removeItem("cran-auth-store");
}

export function consumeAuthTokenFromUrl(): string | null {
  const url = new URL(window.location.href);
  const token = url.searchParams.get(AUTH_TOKEN_PARAM);
  if (!token) {
    return null;
  }
  url.searchParams.delete(AUTH_TOKEN_PARAM);
  window.history.replaceState({}, "", url.toString());
  return token;
}

export function getAuthHeader(): Record<string, string> {
  let token = getAuthToken();
  // Fallback: try reading from URL if localStorage is empty
  if (!token) {
    const url = new URL(window.location.href);
    token = url.searchParams.get(AUTH_TOKEN_PARAM);
  }
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}
