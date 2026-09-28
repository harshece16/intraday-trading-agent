import { clock, dateLabel, joinWords } from "../format";

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
export function GuardNotes({ guards }) {
  if (!guards || guards.off) return null;
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
      {banLine} {bandLine}
    </p>
  );
}
