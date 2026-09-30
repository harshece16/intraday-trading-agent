export function scanRows(s) {
  return (s.scanner && s.scanner.rows) || [];
}
export function rowFor(s, sym) {
  return scanRows(s).find((r) => r.symbol === sym) || null;
}
export function heldSymbols(s) {
  return Object.entries(s.positions).filter(([, p]) => p.quantity !== 0).map(([k]) => k);
}
export function analysisFor(s, sym) {
  const live = sym && s.indicators[sym];
  if (live && live.bull_score !== undefined) return { b: live, live: true };
  const r = sym && rowFor(s, sym);
  if (r && r.brain) return { b: r.brain, live: false };
  return null;
}
// The scanner sets no side (README section 115): the checklist's own reading
// picks it. A side that passes comes first, then the checklist's lean. A
// long-only stock (fixed price band) is never read as a short.
export function checklistSide(r, b) {
  const longOnly = !!(r && r.long_only);
  if (!b) return "long";
  if (b.long_ok) return "long";
  if (b.short_ok && !longOnly) return "short";
  return b.bias === "short" && !longOnly ? "short" : "long";
}
export function isReady(s, r) {
  const a = analysisFor(s, r.symbol);
  return r.status === "ACTIVE" && !!a && (a.b.long_ok || (a.b.short_ok && !r.long_only));
}

export function sentiment(score) {
  if (score >= 0.15) return { word: "Positive", cls: "up" };
  if (score <= -0.15) return { word: "Negative", cls: "down" };
  return { word: "Neutral", cls: "muted" };
}

// Short form of a checklist item's citation string, e.g. "Varsity Technical
// Analysis ch 4-10, and Nison, Japanese Candlestick Charting Techniques"
// -> "Varsity Technical Analysis". Shared by the rule-book chips and the
// one-line rule tag shown on every row, so a stock's call is traceable to a
// named source at a glance, not just inside its own page.
export function shortSource(source) {
  return (source || "").split(",")[0].split(" and ")[0].replace(/ ch [\d.-]+.*/, "").trim();
}

// The single most specific rule driving a stock's brain wiring, for a quick
// tag on list rows. Prefers a confirmed Bulkowski daily pattern (the most
// citation-rich signal); otherwise the strongest passing checklist item from
// its Trader Brain read (only computed for the scanner's top 15, so most
// rows won't have one — that's honest, not every stock gets a deep read).
export function primaryRule(r) {
  if (r.swing_patterns && r.swing_patterns.length) return `Bulkowski: ${r.swing_patterns[0].name}`;
  if (r.brain && r.brain.checklist) {
    const cl = r.brain.checklist[checklistSide(r, r.brain)];
    const hit = cl && cl.items.find((i) => i.ok && i.key === "pattern");
    if (hit) return `${shortSource(hit.source)}: ${cl.pattern || hit.detail}`;
    const any = cl && cl.items.find((i) => i.ok);
    if (any) return shortSource(any.source);
  }
  return null;
}

function hhmmToMinutes(hhmm) {
  const [h, m] = (hhmm || "0:0").split(":").map(Number);
  return h * 60 + m;
}

export function sessionInfo(s) {
  if (!s.server_ts) return null;
  const ist = new Date(s.server_ts * 1000 + 5.5 * 3600 * 1000); // shift to IST, read with getUTC*
  const nowMin = ist.getUTCHours() * 60 + ist.getUTCMinutes() + ist.getUTCSeconds() / 60;
  const openMin = hhmmToMinutes(s.market_open);
  const closeMin = hhmmToMinutes(s.market_close);
  if (s.market_status === "open") {
    const pct = Math.max(0, Math.min(100, ((nowMin - openMin) / (closeMin - openMin)) * 100));
    const left = Math.max(0, Math.round(closeMin - nowMin));
    return { label: `Closes in ${Math.floor(left / 60)}h ${left % 60}m`, pct };
  }
  if (!s.next_open) return null;
  const diffMin = Math.max(0, Math.round((new Date(s.next_open).getTime() - s.server_ts * 1000) / 60000));
  const h = Math.floor(diffMin / 60), m = diffMin % 60;
  const label =
    h >= 24
      ? `Opens ${new Date(s.next_open).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}, ${s.market_open}`
      : `Opens in ${h}h ${m}m`;
  return { label, pct: 0 };
}

export function tradeAction(t) {
  const r = t.reason || "";
  if (t.side === "BUY") return r.endsWith("(long)") ? "Bought" : "Covered short";
  return r.endsWith("(short)") ? "Sold short" : "Sold";
}

export const REASON_TEXT = {
  stop_loss: "Stop-loss hit", take_profit: "Target hit", auto_square_off: "Auto square-off",
  brain_exit: "Exit signal", brain_cover: "Cover signal", signal: "Signal",
  fno_stop_loss: "F&O stop hit", fno_take_profit: "F&O target hit", fno_auto_square_off: "F&O auto square-off",
};
export const KIND_TEXT = {
  scan: "Scan", watchlist: "Watchlist", setup: "Setup forming", trade: "Trade",
  blocked: "Skipped", risk: "Risk", error: "Problem", system: "System",
  summary: "Session summary",
};
