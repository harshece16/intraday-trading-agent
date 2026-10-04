import { useCallback, useEffect, useRef, useState } from "react";

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
// per browser. A ?key= param on the dashboard's own URL seeds it too, and is then
// removed from the address bar; the key is never sent to the backend in a URL (#87).
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
    // Take it straight back out of the address bar, so it doesn't sit in
    // browser history or a screenshot (#87).
    params.delete("key");
    const rest = params.toString();
    history.replaceState(null, "", window.location.pathname + (rest ? `?${rest}` : "") + window.location.hash);
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

// A request that never answers used to leave its button disabled for as long
// as it hung, and one shared "busy" flag meant a hung Pause could lock out
// Stop & close all (#233). Every request now gives up after this long unless
// the caller asks for longer.
export const DEFAULT_TIMEOUT_MS = 10000;

/** fetch() with the dashboard key and a timeout. Throws on a network failure
 *  or a timeout, with a message a person can read. */
export async function apiFetch(path, options = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = options;
  const headers = { ...(rest.headers || {}), "X-Api-Key": API_KEY };
  const ctrl = new AbortController();
  const timer = timeoutMs ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...rest, headers, signal: ctrl.signal });
  } catch (e) {
    if (ctrl.signal.aborted) {
      const err = new Error(`the backend didn't answer within ${Math.round(timeoutMs / 1000)} s`);
      err.timeout = true; // the request may still be running on the backend
      throw err;
    }
    throw new Error(e?.message === "Failed to fetch" || e instanceof TypeError ? "the backend isn't reachable" : e?.message || String(e));
  } finally {
    if (timer) clearTimeout(timer);
  }
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

/** The readable reason out of an error response body. */
function detailText(body, status) {
  const d = body?.detail;
  if (typeof d === "string" && d) return d;
  if (d?.message) return d.message;
  if (typeof body?.reason === "string" && body.reason) return body.reason;
  return `the backend answered ${status}`;
}

/**
 * Opens the Kite login popup. The popup can't send the X-Api-Key header, so
 * the URL is fetched first; the window is opened synchronously (still inside
 * the click) so popup blockers allow it, then pointed at Kite (#87).
 */
export async function openKiteLogin() {
  const win = window.open("", "kite-login", "width=480,height=640");
  if (!win) {
    // A blocked popup used to make Connect Kite do nothing at all (#241).
    throw new Error(`The browser blocked the Kite login window. Allow pop-ups for ${window.location.host || "this site"} (the icon at the right of the address bar), then click again.`);
  }
  // The backend opens the ngrok tunnel Kite redirects back through before it
  // hands over the login URL, which takes a few seconds; say so in the popup.
  const say = (html) => {
    try {
      win.document.body.innerHTML = `<div style="font:15px system-ui;padding:24px;line-height:1.5">${html}</div>`;
    } catch {
      /* already navigated */
    }
  };
  say("Opening the secure tunnel for the Kite login…");
  let data;
  try {
    const res = await apiFetch("/api/kite/login-url", { timeoutMs: 30000 });
    data = await res.json().catch(() => ({}));
  } catch (e) {
    say(`<b>Couldn't reach the backend.</b> ${String(e.message).replace(/</g, "&lt;")}. Is it running on port 8000?`);
    throw new Error(`Couldn't start the Kite login: ${e.message}.`);
  }
  if (data.url) {
    win.location.href = data.url;
    return;
  }
  const why = data.error || detailText(data, "with no login URL");
  say(`<b>Couldn't start the Kite login.</b><br>${String(why).replace(/</g, "&lt;")}`);
  throw new Error(`Couldn't start the Kite login: ${why}`);
}

/** Downloads an authenticated file (the key goes in the header, not the URL). */
export async function downloadWithKey(path, filename) {
  const res = await apiFetch(path, { timeoutMs: 60000 });
  if (!res.ok) throw new Error(detailText(await res.json().catch(() => ({})), res.status));
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function apiJson(path, options) {
  const res = await apiFetch(path, options);
  if (!res.ok) throw new Error(detailText(await res.json().catch(() => ({})), res.status));
  return res.json();
}

/** GET `path` (again every `intervalMs`, if given). A failed load is shown, not swallowed:
 *  pages used to `.catch(() => {})` and sit on "Loading…" forever. Null path = don't fetch. */
export function useApi(path, intervalMs) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) return undefined;
    let alive = true;
    const load = () => apiJson(path)
      .then((d) => { if (alive) { setData(d); setError(null); } })
      .catch((e) => { if (alive) setError(e.message); });
    load();
    const t = intervalMs ? setInterval(load, intervalMs) : null;
    return () => { alive = false; if (t) clearInterval(t); };
  }, [path, intervalMs, tick]);
  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { data, error, reload, setData };
}

/** The one POST path. Throws an Error whose message is the backend's reason;
 *  a refused switch to live carries the reasons in `err.blockers`. */
export async function postJson(path, body, { timeoutMs } = {}) {
  const res = await apiFetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    timeoutMs,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(detailText(data, res.status));
    err.blockers = data?.detail?.blockers || [];
    err.status = res.status;
    throw err;
  }
  return data;
}

/**
 * A button's request: `busy` while it runs (always cleared, in `finally`),
 * and the failure's reason in `error` (#236). `run(...args)` resolves to
 * `{ ok: true, value }` or `{ ok: false, error }` and never throws.
 */
export function useAction(fn) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const fnRef = useRef(fn);
  useEffect(() => { fnRef.current = fn; });
  const run = useCallback(async (...args) => {
    setBusy(true);
    setError(null);
    try {
      return { ok: true, value: await fnRef.current(...args) };
    } catch (e) {
      setError(e?.message || String(e));
      return { ok: false, error: e };
    } finally {
      setBusy(false);
    }
  }, []);
  const clearError = useCallback(() => setError(null), []);
  return { run, busy, error, clearError };
}

/** Paper/Live. Going live can be refused by the backend (409) with the reasons in err.blockers. */
export function setTradingMode(paperMode) {
  return postJson("/api/mode", { paper_mode: paperMode });
}

export function setEntriesPaused(paused) {
  return postJson("/api/control/pause", { paused });
}

/** Kill switch: pause entries, close every position at market, back to Paper. */
export function stopAndCloseAll() {
  // Closing several positions with real orders can take longer than the
  // default; a timeout here would report failure while the backend carries on.
  return postJson("/api/control/stop", undefined, { timeoutMs: 45000 });
}

export function setTelegramEnabled(enabled) {
  return postJson("/api/alerts/telegram/enable", { enabled });
}

export function sendTelegramTest() {
  return postJson("/api/alerts/telegram/test");
}

/** Shows why a switch to live was refused. Returns true if it was a refusal. */
export function explainRefusal(err) {
  if (!err?.blockers?.length) return false;
  alert(`${err.message}:\n\n• ${err.blockers.join("\n• ")}`);
  return true;
}

// How long the WebSocket may stay silent before the dashboard asks
// /api/state itself. The engine pushes every ~3 s.
const WS_SILENCE_MS = 8000;

/** Live app state over the WebSocket, with automatic reconnect. */
export function useAppState() {
  const [state, setState] = useState(null);
  const wsRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    let stopped = false;
    let lastMessageAt = Date.now();
    let lastPollAt = 0;
    let polling = false;
    let newestTs = 0;

    // Only a real snapshot, and never one older than what's on screen: the
    // backup poll used to swap in a JSON error body, or an older snapshot
    // that arrived after a newer push (#239).
    function accept(snap) {
      if (stopped || !snap || typeof snap !== "object" || !("paper_mode" in snap)) return;
      const ts = Number(snap.server_ts) || 0;
      if (ts && ts < newestTs) return;
      if (ts) newestTs = ts;
      setState(snap);
    }

    function connect() {
      if (stopped) return;
      // The key goes in the first message, not the URL: uvicorn logs every
      // request line, and it used to write the key to backend.log (#87).
      const ws = new WebSocket(API_BASE.replace(/^http/, "ws") + "/ws");
      wsRef.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ type: "auth", key: API_KEY }));
      ws.onmessage = (evt) => {
        lastMessageAt = Date.now();
        try { accept(JSON.parse(evt.data)); } catch { /* not a snapshot */ }
      };
      ws.onclose = () => {
        if (!stopped) timerRef.current = setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
    }
    connect();

    // Belt and braces, in case the socket silently stalls without firing
    // onclose: ask /api/state only once the socket has been quiet a while.
    const pollId = setInterval(async () => {
      const now = Date.now();
      if (polling || now - lastMessageAt < WS_SILENCE_MS || now - lastPollAt < WS_SILENCE_MS) return;
      polling = true;
      lastPollAt = now;
      try {
        const res = await apiFetch("/api/state");
        if (res.ok) accept(await res.json());
      } catch {
        /* the backend is down; the WebSocket reconnect loop keeps trying */
      } finally {
        polling = false;
      }
    }, 2000);

    return () => {
      stopped = true;
      clearTimeout(timerRef.current);
      clearInterval(pollId);
      wsRef.current?.close();
    };
  }, []);

  return state;
}
