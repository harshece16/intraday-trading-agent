import { clock, dateLabel, joinWords } from "../format";

// Where the scan's prices came from. The delayed feed is named as such, with the reason.
export function feedText(feed) {
  if (!feed) return "";
  if (feed.prices === "live") {
    const when = feed.quotes_at ? new Date(feed.quotes_at) : null;
    const day = when && when.toDateString() !== new Date().toDateString()
      ? `${when.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}, ` : "";
    const at = when ? ` as of ${day}${when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "";
    const mixed = feed.rows_delayed ? ` (${feed.rows_delayed} ${feed.rows_delayed === 1 ? "stock is" : "stocks are"} on the delayed feed)` : "";
    return `Prices are live from Kite${at}${mixed}.`;
  }
  return `Prices are from the delayed feed, about 15 minutes late. ${feed.why_delayed || ""}`.trim();
}

// When the day's list was fixed, in words. Empty until it is fixed.
export function fixedText(selection) {
  if (!selection || selection.mode !== "liquidity" || !selection.fixed) return "";
  const at = selection.fixed_at ? ` at ${clock(selection.fixed_at)}` : "";
  return selection.fixed_when === "before the open"
    ? `Fixed before the open${at}, from daily data.`
    : `Fixed at the first scan of the session${at}, because no read ran before the open.`;
}

// What the two NSE guard files say about the NIFTY 100 today. A file that
// could not be read is said to be unread, never shown as "nothing found".
export function GuardNotes({ guards, feed }) {
  if (!guards || guards.off) return feed ? <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>{feedText(feed)}</p> : null;
  const { ban, bands } = guards;
  const banLine = !ban
    ? "F&O ban list: could not be read, so no stock is left out for it."
    : ban.in_universe.length
    ? `F&O ban list for ${dateLabel(ban.trade_date)}: ${joinWords(ban.in_universe)} ${ban.in_universe.length === 1 ? "is" : "are"} left alone today.`
    : `F&O ban list for ${dateLabel(ban.trade_date)}: no NIFTY 100 stock is on it (${ban.count} elsewhere).`;
  const flagged = bands ? [...new Set([...bands.not_eq, ...bands.surveillance])] : [];
  const bandLine = !bands
    ? "Price-band list: could not be read, so no stock is held to longs for it."
    : `${bands.banded.length ? `${joinWords(bands.banded)} ${bands.banded.length === 1 ? "has" : "have"} a fixed price band: long only, and left alone within 2% of the band.` : "No NIFTY 100 stock has a fixed price band today."}${flagged.length ? ` ${joinWords(flagged)} ${flagged.length === 1 ? "is" : "are"} in trade-for-trade or under surveillance and left alone.` : ""}`;
  return (
    <p className="muted" style={{ fontSize: 13, marginTop: -6 }}>
      {feed ? `${feedText(feed)} ` : ""}{banLine} {bandLine}
    </p>
  );
}
