const AUTH_TOKEN_KEY = "cran_auth_token";
const AUTH_TOKEN_TIMESTAMP_KEY = "cran_auth_token_ts";
const AUTH_TOKEN_PARAM = "token";
const TOKEN_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

function _looksLikeJwt(token: string): boolean {
  return token.split(".").length === 3;
}

export function getAuthToken(): string | null {
  const v1Token = localStorage.getItem(AUTH_TOKEN_KEY);
  const v2Token = localStorage.getItem("cran_v2_auth_token");
  // Prefer v2 JWT if both exist; v1 token is usually a short random string
  if (v2Token && _looksLikeJwt(v2Token)) {
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
