import { useEffect, useRef, useState } from "react";

const params = new URLSearchParams(window.location.search);
const apiOverride = params.get("api");
export const API_BASE =
  apiOverride && /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(apiOverride)
    ? apiOverride
    : window.location.hostname === ""
    ? "http://localhost:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;

export const IST_OFFSET_S = 19800;

// The backend requires this on every request except the Kite OAuth endpoints
// (see backend/app.py's ApiKeyMiddleware) — asked for once, then remembered
// per browser. A ?key= URL param seeds it too (convenience + testing).
function getApiKey() {
  let key = null;
  const fromUrl = params.get("key");
  try {
    key = fromUrl || localStorage.getItem("dashboardApiKey");
  } catch (e) {
    /* private window etc. */
  }
  if (fromUrl) {
    try {
      localStorage.setItem("dashboardApiKey", fromUrl);
    } catch (e) {
      /* ignore */
    }
  }
  if (!key) {
    key = prompt("Enter the dashboard API key (see backend/.dashboard_key.json or the startup log):") || "";
    try {
      localStorage.setItem("dashboardApiKey", key);
    } catch (e) {
      /* ignore */
    }
  }
  return key;
}

export const API_KEY = getApiKey();

export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}), "X-Api-Key": API_KEY };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    try {
      localStorage.removeItem("dashboardApiKey");
    } catch (e) {
      /* ignore */
    }
    alert("Dashboard API key was rejected — reloading to ask again.");
    location.reload();
  }
  return res;
}

export async function apiJson(path, options) {
  const res = await apiFetch(path, options);
  return res.json();
}

/** Live app state over the WebSocket, with automatic reconnect. */
export function useAppState() {
  const [state, setState] = useState(null);
  const wsRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    let stopped = false;

    function connect() {
      if (stopped) return;
      const ws = new WebSocket(API_BASE.replace(/^http/, "ws") + "/ws?key=" + encodeURIComponent(API_KEY));
      wsRef.current = ws;
      ws.onmessage = (evt) => setState(JSON.parse(evt.data));
      ws.onclose = () => {
        if (!stopped) timerRef.current = setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
    }
    connect();

    // Belt-and-braces poll, in case the socket silently stalls without firing onclose.
    const pollId = setInterval(async () => {
      try {
        const res = await apiFetch("/api/state");
        if (!stopped) setState(await res.json());
      } catch (e) {
        /* the WebSocket is probably already delivering updates */
      }
    }, 10000);

    return () => {
      stopped = true;
      clearTimeout(timerRef.current);
      clearInterval(pollId);
      wsRef.current?.close();
    };
  }, []);

  return state;
}
