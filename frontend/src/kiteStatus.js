/* One place that turns /api/kite/status into what the UI shows, so the header
   chip, the Overview banner and anything else added later can't drift apart
   and tell the user two different stories about the same session. */

import { dateTimeIST } from "./format.js";

export const KITE_STATES = {
  // "Kite: live prices", not "Kite live": in Paper, "live" read as live trading (#245).
  connected: { label: "Kite: live prices", tone: "ok", action: "Reconnect" },
  expired: { label: "Kite session expired", tone: "bad", action: "Reconnect" },
  disconnected: { label: "Kite not connected", tone: "idle", action: "Connect Kite" },
  not_configured: { label: "Delayed prices", tone: "idle", action: "Connect Kite" },
  error: { label: "Kite unreachable", tone: "warn", action: "Retry" },
};

/** "in 6h 20m" / "2h ago" — a duration a person can act on, from seconds. */
export function relativeDuration(seconds) {
  if (seconds === null || seconds === undefined) return null;
  const past = seconds < 0;
  const s = Math.abs(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const text = h >= 1 ? `${h}h ${m}m` : `${Math.max(m, 1)}m`;
  return past ? `${text} ago` : `in ${text}`;
}

/** An ISO timestamp as "5 Oct, 06:00 IST", or null (#243). */
export function localTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : dateTimeIST(d);
}

/** Stand-in for `reason` when talking to a backend that predates it. Says
 *  less than the real thing, because the old payload knows less. */
function legacyReason(state, k) {
  if (state === "connected") {
    return k.using_live_data
      ? "Logged in to Kite. Live prices and live order routing are available."
      : "Logged in to Kite, but the engine is still on the delayed feed.";
  }
  if (state === "not_configured") return "Kite API key and secret aren't set.";
  return "Not logged in to Kite yet. Click Connect Kite.";
}

/**
 * @param {object|null} k the /api/kite/status payload, or null while loading
 * @returns {{label:string, tone:string, action:string, reason:string,
 *            detail:string, urgent:boolean, loading:boolean}}
 */
export function describeKite(k) {
  if (!k) {
    return { label: "Checking Kite…", tone: "idle", action: "Connect Kite", reason: "",
             detail: "", redirectUrl: "", loginStalled: false, urgent: false, loading: true };
  }
  // A backend older than this file doesn't send `state` at all. Defaulting a
  // missing field to "disconnected" made the dashboard report "Kite not
  // connected" over a live, working session — the same confidently-wrong
  // display this module exists to prevent, just with the sign flipped.
  // Derive it from the legacy fields instead, and only then fall back.
  const derived = k.state
    || (!k.app_configured ? "not_configured" : k.connected ? "connected" : "disconnected");
  const base = KITE_STATES[derived] || KITE_STATES.disconnected;
  k = { ...k, state: derived, reason: k.reason || legacyReason(derived, k) };
  // Connected but the engine is still on the delayed feed is its own case:
  // the login worked, so "expired" would be wrong, but so would "live".
  const live = k.state === "connected" && k.using_live_data;
  const label = k.state === "connected" && !live ? "Kite: delayed prices" : base.label;
  const tone = k.state === "connected" && !live ? "warn" : base.tone;

  const lines = [k.reason];
  if (k.state === "connected" && !k.using_live_data) {
    lines.push("Prices are still coming from the delayed free feed (USE_KITE_DATA is off).");
  }
  if (k.generated_at) lines.push(`Logged in ${localTime(k.generated_at)}.`);
  if (k.expires_at) {
    const rel = relativeDuration(k.seconds_until_expiry);
    lines.push(k.seconds_until_expiry > 0
      ? `Expires ${localTime(k.expires_at)} (${rel}) — Kite ends every session at 06:00 IST.`
      : `Expired ${localTime(k.expires_at)} (${rel}).`);
  }
  if (k.probed) lines.push("Confirmed against Kite just now.");
  // Only when it can matter. A working session proves the redirect is fine,
  // and repeating it on every hover would be noise.
  if (k.state !== "connected" && k.redirect_url) {
    lines.push(`Zerodha must redirect back to: ${k.redirect_url}`);
    lines.push("That exact URL has to be registered at developers.kite.trade and reachable.");
  }

  return {
    label: k.login_stalled ? "Kite login didn't return" : label,
    tone: k.login_stalled ? "bad" : tone,
    action: base.action,
    reason: k.reason || "",
    detail: lines.filter(Boolean).join("\n"),
    redirectUrl: k.redirect_url || "",
    // A login that went out and never came back is its own failure: the
    // button appears to do nothing, and nothing in the app says why.
    loginStalled: !!k.login_stalled,
    // Worth pulling the eye to: it was working and now isn't, or it broke.
    urgent: k.state === "expired" || k.state === "error" || !!k.login_stalled,
    loading: false,
  };
}
