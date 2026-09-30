import { useEffect, useRef } from "react";
import { enabled, fire } from "./notifications";

const FLAT_THRESHOLD_PCT = 1.5; // used when a symbol's real ATR% isn't known yet

/** Fires a browser notification for every NEW trade fill, risk warning and
 * momentum-book line (a rebalance, or its evening job failing) in
 * the activity log (state.activity, already pushed over the WebSocket every
 * page reads), and for a real price move on a watched/held symbol past a
 * threshold derived from that symbol's own real ATR% (half a day's typical
 * range — a flat 1.5% fallback only when ATR% isn't known for it yet). Runs
 * once, globally, from App.jsx's Shell — not per-page — so alerts still fire
 * no matter which tab is open. */
export function useAlerts(state) {
  const lastActivityTs = useRef(0);
  const seededActivity = useRef(false);
  const lastNotifiedPrice = useRef({});

  useEffect(() => {
    if (!state || !enabled()) return;

    const items = state.activity || [];
    if (!seededActivity.current) {
      // First state we see — remember the latest ts without notifying, so
      // turning alerts on doesn't replay the whole recent history at once.
      lastActivityTs.current = items[0]?.ts || 0;
      seededActivity.current = true;
    } else if (items.length) {
      const fresh = items.filter((a) => a.ts > lastActivityTs.current);
      for (const a of fresh.slice().reverse()) {
        if (a.kind === "trade") {
          fire(a.symbol ? `${a.symbol} — trade` : "Trade", a.message, `trade-${a.ts}`);
        } else if (a.kind === "momentum") {
          fire("Trader Sahab — momentum book", a.message, `momentum-${a.ts}`);
        } else if (a.level === "warn" || a.level === "error") {
          fire("Trader Sahab — risk alert", a.message, `risk-${a.ts}`);
        }
      }
      lastActivityTs.current = Math.max(lastActivityTs.current, items[0].ts);
    }

    const rows = (state.scanner && state.scanner.rows) || [];
    const atrBySymbol = Object.fromEntries(rows.map((r) => [r.symbol, r.atr_pct]));
    const held = new Set(Object.entries(state.positions || {}).filter(([, p]) => p.quantity !== 0).map(([sym]) => sym));
    const watched = new Set([...(state.watchlist || []), ...held]);
    for (const sym of watched) {
      const ltp = state.indicators?.[sym]?.ltp;
      if (!ltp) continue;
      const last = lastNotifiedPrice.current[sym];
      if (last == null) {
        lastNotifiedPrice.current[sym] = ltp;
        continue;
      }
      const movePct = ((ltp - last) / last) * 100;
      const atrPct = atrBySymbol[sym];
      const threshold = atrPct ? Math.max(0.5, atrPct * 0.5) : FLAT_THRESHOLD_PCT;
      if (Math.abs(movePct) >= threshold) {
        fire(
          `${sym} ${movePct >= 0 ? "+" : ""}${movePct.toFixed(1)}%`,
          `Now ${ltp.toFixed(2)}${held.has(sym) ? " — open position" : ""}`,
          `price-${sym}`,
        );
        lastNotifiedPrice.current[sym] = ltp;
      }
    }
  }, [state]);
}
