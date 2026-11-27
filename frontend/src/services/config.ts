/**
 * Runtime configuration and URL resolvers for Blind Billion 2.0.
 */

/**
 * Normalizes and resolves the API base URL.
 * Falls back to "/api" if not provided or empty.
 */
export function getApiBaseUrl(envUrl?: string): string {
  if (!envUrl) {
    return "/api";
  }
  const trimmed = envUrl.trim().replace(/\/+$/, "");
  if (!trimmed || trimmed === "/api") {
    return "/api";
  }

  // If a full URL is provided, ensure it ends with /api if not already present
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    if (!trimmed.endsWith("/api")) {
      return `${trimmed}/api`;
    }
    return trimmed;
  }

  // Relative path
  if (!trimmed.endsWith("/api") && trimmed !== "") {
    return `${trimmed}/api`;
  }
  return trimmed;
}

/**
 * Normalizes and resolves the WebSocket endpoint URL for a given room and token.
 */
export function getWebSocketUrl(
  roomCode: string,
  token: string,
  envWsUrl?: string,
  location?: { protocol: string; host: string }
): string {
  const code = encodeURIComponent(roomCode.trim().toUpperCase());
  const tok = encodeURIComponent(token);
  const loc = location || (typeof window !== "undefined" ? window.location : { protocol: "http:", host: "localhost:5173" });

  if (envWsUrl && envWsUrl.trim()) {
    let base = envWsUrl.trim().replace(/\/+$/, "");

    // Convert http(s) to ws(s)
    if (base.startsWith("http://")) {
      base = `ws://${base.slice(7)}`;
    } else if (base.startsWith("https://")) {
      base = `wss://${base.slice(8)}`;
    }

    // Handle relative or protocol-relative paths
    if (base.startsWith("//")) {
      const proto = loc.protocol === "https:" ? "wss:" : "ws:";
      base = `${proto}${base}`;
    } else if (base.startsWith("/")) {
      const proto = loc.protocol === "https:" ? "wss:" : "ws:";
      base = `${proto}//${loc.host}${base}`;
    } else if (!base.startsWith("ws://") && !base.startsWith("wss://")) {
      const proto = loc.protocol === "https:" ? "wss:" : "ws:";
      base = `${proto}//${base}`;
    }

    if (!base.endsWith("/ws")) {
      base = `${base}/ws`;
    }
    return `${base}/rooms/${code}?token=${tok}`;
  }

  // Unset or empty: derive from current window location
  const proto = loc.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${loc.host}/ws/rooms/${code}?token=${tok}`;
}
