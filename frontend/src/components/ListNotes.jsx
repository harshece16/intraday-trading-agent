import { clock, clockIST, dateLabel, istDay, joinWords } from "../format";

// Where the scan's prices came from. The delayed feed is named as such, with the reason.
export function feedText(feed) {
  if (!feed) return "";
  if (feed.prices === "live") {
    const when = feed.quotes_at || null;
    const day = when && istDay(when) !== istDay(new Date()) ? `${dateLabel(istDay(when))}, ` : "";
    const at = when ? ` as of ${day}${clockIST(when)}` : "";
    const mixed = feed.rows_delayed ? ` (${feed.rows_delayed} ${feed.rows_delayed === 1 ? "stock is" : "stocks are"} on the delayed feed)` : "";
    return `Prices are live from Kite${at}${mixed}.`;
  }
  return `Prices are from the delayed feed. ${feed.why_delayed || ""}`.trim();
}

// When the day's list was fixed, in words. Empty until it is fixed.
export function fixedText(selection) {
  if (!selection || selection.mode !== "liquidity" || !selection.fixed) return "";
  const at = selection.fixed_at ? ` at ${clock(selection.fixed_at)}` : "";
  return selection.fixed_when === "before the open"
    ? `Fixed before the open${at}, from daily data.`
    : `Fixed at the first scan of the session${at}, because no read ran before the open.`;
}

// Why a guard file is unread: when its last fetch failed, and when NSE is
// asked again (scanner.guards_summary "unread", #212).
function unreadText(failed) {
  if (!failed) return "";
  return ` (the last try, at ${clock(failed.at)}, failed: ${failed.error}; tried again after ${clock(failed.retry_at)})`;
}

// What the two NSE guard files say about the NIFTY 100 today. A file that
// could not be read is said to be unread, never shown as "nothing found".
export function GuardNotes({ guards, feed }) {
  if (!guards || guards.off) return feed ? <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>{feedText(feed)}</p> : null;
  const { ban, bands } = guards;
  const unread = guards.unread || {};
  const banLine = !ban
    ? `F&O ban list: could not be read${unreadText(unread.ban)}, so no stock is left out for it.`
    : ban.in_universe.length
    ? `F&O ban list for ${dateLabel(ban.trade_date)}: ${joinWords(ban.in_universe)} ${ban.in_universe.length === 1 ? "is" : "are"} left alone today.`
    : `F&O ban list for ${dateLabel(ban.trade_date)}: no NIFTY 100 stock is on it (${ban.count} elsewhere).`;
  const flagged = bands ? [...new Set([...bands.not_eq, ...bands.surveillance])] : [];
  const bandLine = !bands
    ? `Price-band list: could not be read${unreadText(unread.bands)}, so no stock is held to longs for it.`
    : `${bands.banded.length ? `${joinWords(bands.banded)} ${bands.banded.length === 1 ? "has" : "have"} a fixed price band: long only, and left alone within 2% of the band.` : "No NIFTY 100 stock has a fixed price band today."}${flagged.length ? ` ${joinWords(flagged)} ${flagged.length === 1 ? "is" : "are"} in trade-for-trade or under surveillance and left alone.` : ""}`;
  return (
    <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>
      {feed ? `${feedText(feed)} ` : ""}{banLine} {bandLine}
    </p>
  );
}

// The industries whose real sector index had too little daily history for
// its trend (#197). Their stocks are scored without that check, and the
// page says so rather than leaving the gap unseen.
export function SectorTrendNote({ scanner }) {
  const gone = scanner?.sector_trends_unavailable;
  if (!gone || !gone.length) return null;
  const n = (scanner.rows || []).filter((r) => gone.includes(r.industry)).length;
  return (
    <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>
      Sector trend unavailable for {joinWords(gone)}: too little daily history for {gone.length === 1 ? "its index" : "their indices"}, so {n} {n === 1 ? "stock is" : "stocks are"} scored without that check.
    </p>
  );
}
