/* One place that turns /api/kite/status into what the UI shows, so the header
   chip, the Overview banner and anything else added later can't drift apart
   and tell the user two different stories about the same session. */

export const KITE_STATES = {
  connected: { label: "Kite live", tone: "ok", action: "Reconnect" },
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

/** Local time of an ISO timestamp, or null — the backend sends IST-aware ISO. */
export function localTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleString([], {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

/**
 * @param {object|null} k the /api/kite/status payload, or null while loading
 * @returns {{label:string, tone:string, action:string, reason:string,
 *            detail:string, urgent:boolean, loading:boolean}}
 */
export function describeKite(k) {
  if (!k) {
    return { label: "Checking Kite…", tone: "idle", action: "Connect Kite", reason: "",
             detail: "", urgent: false, loading: true };
  }
  const base = KITE_STATES[k.state] || KITE_STATES.disconnected;
  // Connected but the engine is still on the delayed feed is its own case:
  // the login worked, so "expired" would be wrong, but so would "live".
  const live = k.state === "connected" && k.using_live_data;
  const label = k.state === "connected" && !live ? "Kite connected" : base.label;
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

  return {
    label,
    tone,
    action: base.action,
    reason: k.reason || "",
    detail: lines.filter(Boolean).join("\n"),
    // Worth pulling the eye to: it was working and now isn't, or it broke.
    urgent: k.state === "expired" || k.state === "error",
    loading: false,
  };
}
