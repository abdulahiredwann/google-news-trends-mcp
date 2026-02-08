const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Fire a custom event to tell AuthProvider to log out and redirect.
 */
function triggerLogout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
  window.dispatchEvent(new Event("auth:logout"));
}

/**
 * Base fetch wrapper that adds auth headers and handles errors.
 */
export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem("access_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    triggerLogout();
  }

  return res;
}

/**
 * Returns the full URL for SSE streaming (no fetch wrapper needed).
 */
export function getApiBase(): string {
  return API_BASE;
}

/**
 * Exported so streamChat can also trigger logout on 401.
 */
export { triggerLogout };
