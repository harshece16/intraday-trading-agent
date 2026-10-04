import { useEffect } from "react";
import { downloadWithKey, useAction, useApi } from "../api";
import LoadState from "../components/LoadState";
import { clock, dateLabel, inr, istDay, money, num, tone } from "../format";
import { REASON_TEXT, tradeAction } from "../helpers";
import SymLink from "../components/SymLink";

// Trades arrive newest-first (state.py inserts each new trade at index 0), but a
// running net only makes sense accumulated oldest-to-newest, so walk the array in
// reverse. t.realized is net of both legs' charges since issue #21 — this comment
// claimed that before it was true, and the "check" behind the claim only compared
// this total against tax.net_pnl, which was built from the same gross field.
function runningNetById(trades) {
  let sum = 0;
  const byId = {};
  for (let i = trades.length - 1; i >= 0; i--) {
    sum += trades[i].realized || 0;
    byId[trades[i].id] = sum;
  }
  return byId;
}

// Today's tax figures from today's legs only, the same sums as the backend's
// _tax_summary. state.trades used to keep earlier days' legs after the day
// changed, so the backend's own figure counted them as today (#247).
function taxOf(trades) {
  const gross = (t) => (t.realized_gross != null ? t.realized_gross : t.realized || 0);
  const closed = trades.filter((t) => t.realized);
  return {
    turnover: closed.reduce((a, t) => a + Math.abs(gross(t)), 0),
    net_pnl: closed.reduce((a, t) => a + t.realized, 0),
    gross_pnl: closed.reduce((a, t) => a + gross(t), 0),
    charges: trades.reduce((a, t) => a + (t.charges || 0), 0),
  };
}

const EXIT_REASONS = new Set(Object.keys(REASON_TEXT));

/** Journal legs (newest first) into round trips: one per position, its first
 *  leg the entry and the rest its exits. Newest first. */
function roundTrips(legs) {
  const byPos = new Map();
  for (const t of legs) {
    const k = t.position_id || t.id;
    if (!byPos.has(k)) byPos.set(k, []);
    byPos.get(k).push(t);
  }
  const out = [];
  for (const [id, ls] of byPos) {
    ls.sort((a, b) => a.ts - b.ts);
    // A position whose entry fell outside the loaded window shows its exits only.
    const hasEntry = !EXIT_REASONS.has(ls[0].reason);
    const entry = hasEntry ? ls[0] : null;
    const exits = hasEntry ? ls.slice(1) : ls;
    const first = ls[0];
    const exitQty = exits.reduce((a, t) => a + (t.quantity || 0), 0);
    const sum = (f) => exits.reduce((a, t) => a + (f(t) || 0), 0);
    const last = exits[exits.length - 1];
    out.push({
      id, ts: first.ts, day: istDay(first.ts), symbol: first.symbol, mode: first.mode,
      side: entry ? (entry.side === "BUY" ? "LONG" : "SHORT") : (first.side === "BUY" ? "SHORT" : "LONG"),
      qty: entry ? entry.quantity : exitQty,
      entryPrice: entry?.price ?? null, entryTs: entry?.ts ?? null, setup: entry?.reason || null,
      exitPrice: exitQty ? exits.reduce((a, t) => a + t.quantity * t.price, 0) / exitQty : null,
      exitTs: last?.ts ?? null, exitReason: last ? REASON_TEXT[last.reason] || last.reason : null,
      open: !exits.length,
      gross: exits.length ? sum((t) => (t.realized_gross != null ? t.realized_gross : t.realized)) : null,
      charges: ls.reduce((a, t) => a + (t.charges || 0), 0),
      net: exits.length ? sum((t) => t.realized) : null,
      r: exits.some((t) => t.r_multiple != null) ? sum((t) => t.r_multiple) : null,
    });
  }
  return out.sort((a, b) => b.ts - a.ts);
}

function ModePill({ mode }) {
  return mode === "live" ? <span className="pill short">Live</span> : <span className="pill neutral">Paper</span>;
}

function weekdayLabel(day) {
  const d = new Date(`${day}T12:00:00+05:30`);
  return `${d.toLocaleDateString("en-IN", { weekday: "short", timeZone: "Asia/Kolkata" })} ${dateLabel(day)}`;
}

/** Every round trip in the journal, by day, newest first (paper and live). */
function History({ q }) {
  if (!q.data) return <LoadState error={q.error && `trade history: ${q.error}`} onRetry={q.reload} label="Loading the trade history…" />;
  const trips = roundTrips(q.data);
  if (!trips.length) return <p className="empty">No trades in the journal yet.</p>;
  const days = [];
  for (const t of trips) {
    if (!days.length || days[days.length - 1].day !== t.day) days.push({ day: t.day, trips: [] });
    days[days.length - 1].trips.push(t);
  }
  return (
    <>
      {q.error && <LoadState error={`the last update failed (${q.error}); showing the earlier list`} onRetry={q.reload} />}
      {days.map(({ day, trips: ts }) => {
        const net = ts.reduce((a, t) => a + (t.net || 0), 0);
        const closed = ts.filter((t) => !t.open).length;
        return (
          <section key={day} style={{ marginTop: 20 }}>
            <h3 className="h" style={{ fontSize: 15, display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
              {weekdayLabel(day)}
              <span className="muted" style={{ fontSize: 13 }}>
                {ts.length} trade{ts.length === 1 ? "" : "s"}{closed ? <>, net <span className={tone(net)}>{money(net)}</span></> : ""}
              </span>
            </h3>
            <div className="table-wrap">
              <table className="datatable">
                <thead>
                  <tr>
                    <th>Time (IST)</th><th>Stock</th><th>Side</th><th className="num">Qty</th><th className="num">Entry</th>
                    <th className="num">Exit</th><th>Why</th><th className="num">Gross</th><th className="num">Charges</th>
                    <th className="num">Net</th><th className="num">R</th><th>Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {ts.map((t) => (
                    <tr key={t.id}>
                      <td>{t.entryTs ? clock(t.entryTs) : "—"}{t.exitTs ? `–${clock(t.exitTs)}` : t.open ? " (open)" : ""}</td>
                      <td><SymLink sym={t.symbol} /></td>
                      <td className={t.side === "LONG" ? "up" : "down"}>{t.side === "LONG" ? "Long" : "Short"}</td>
                      <td className="num">{t.qty}</td>
                      <td className="num">{t.entryPrice != null ? num(t.entryPrice) : "—"}</td>
                      <td className="num">{t.exitPrice != null ? num(t.exitPrice) : "—"}</td>
                      <td>{[t.setup, t.exitReason].filter(Boolean).join(" → ") || "—"}</td>
                      <td className={`num ${tone(t.gross)}`}>{t.gross != null ? money(t.gross) : "—"}</td>
                      <td className="num muted">{inr(t.charges, 2)}</td>
                      <td className={`num ${tone(t.net)}`}><strong>{t.net != null ? money(t.net) : "open"}</strong></td>
                      <td className="num">{t.r != null ? `${t.r > 0 ? "+" : ""}${t.r.toFixed(2)}R` : "—"}</td>
                      <td><ModePill mode={t.mode} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </>
  );
}

export default function Trades({ state: s }) {
  const today = istDay(new Date());
  // Only today's legs, whatever the snapshot still holds from earlier days (#247).
  const todays = (s.trades || []).filter((t) => istDay(t.ts) === today);
  const tax = taxOf(todays);
  const runningNet = runningNetById(todays);
  const exportCsv = useAction(() => downloadWithKey("/api/journal/trades.csv", "trader-sahab-trades.csv"));
  const history = useApi("/api/journal/trades?limit=2000");
  const { reload } = history;
  // A new fill today shows up in the history as well.
  useEffect(() => { if (todays.length) reload(); }, [todays.length, reload]);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
        <h2 className="h">Trades</h2>
        <button className="btn" disabled={exportCsv.busy} onClick={exportCsv.run}>
          {exportCsv.busy ? "Exporting…" : "Export full history (CSV)"}
        </button>
      </div>
      {exportCsv.error && <p className="down" role="alert">Couldn't export: {exportCsv.error}.</p>}
      <p className="sub">Today's orders first, live as they happen, then every trade in the journal by day, paper and
        live (marked by mode). The export has every leg, for your own records at filing time.</p>
      <h3 className="h" style={{ fontSize: 16, marginTop: 8 }}>Today</h3>
      <div className="tax">
        Intraday equity counts as <strong>speculative business income</strong>. So far: turnover <strong>₹{num(tax.turnover, 0)}</strong>{" "}
        (each closed trade's profit or loss before charges, added up without signs). P&amp;L{" "}
        <strong className={tone(tax.gross_pnl)}>{money(tax.gross_pnl)}</strong> gross, minus{" "}
        <strong>₹{num(tax.charges, 0)}</strong> of brokerage, STT, exchange fees, GST and stamp duty, leaves{" "}
        <strong className={tone(tax.net_pnl)}>{money(tax.net_pnl)}</strong> net. Charges are a deductible business expense, not a
        reduction of turnover. Speculative losses only offset speculative gains and carry forward 4 years.
        Advance tax is due by 15 Jun, 15 Sep, 15 Dec and 15 Mar. Source: Zerodha Varsity, Markets and Taxation; check with a CA.
      </div>
      <div className="table-wrap" style={{ marginTop: 16 }}>
        <table className="datatable">
          <thead><tr><th>Time (IST)</th><th>Stock</th><th>Action</th><th>Shares</th><th>Price</th><th>Invested</th><th>Charges</th><th>P&amp;L</th><th>Running net</th><th>Why</th><th>Mode</th></tr></thead>
          <tbody>
            {todays.length ? todays.map((t) => {
              const action = tradeAction(t);
              const opening = action === "Bought" || action === "Sold short";
              const reason = REASON_TEXT[t.reason] || t.reason || "";
              return (
                <tr key={t.id}>
                  <td>{clock(t.ts)}</td><td><SymLink sym={t.symbol} /></td>
                  <td className={opening ? (t.side === "BUY" ? "up" : "down") : ""}>{action}</td>
                  <td>{t.quantity}</td><td>{num(t.price)}</td>
                  <td>₹{num(t.quantity * t.price, 0)}</td>
                  <td className="muted">{t.charges != null ? `₹${num(t.charges, 2)}` : "—"}</td>
                  <td className={opening ? "" : tone(t.realized)}>
                    {opening ? "—" : <>
                      {money(t.realized)}
                      {t.realized_gross != null && Math.abs(t.realized_gross - t.realized) >= 0.01 && (
                        <div className="muted" style={{ fontSize: 11.5, fontWeight: 400 }}>
                          {money(t.realized_gross)} before ₹{num(t.realized_gross - t.realized, 2)} charges
                        </div>
                      )}
                    </>}
                  </td>
                  <td className={tone(runningNet[t.id])}>{money(runningNet[t.id])}</td>
                  <td>{[reason, t.note].filter(Boolean).join(": ") || "—"}</td>
                  <td><ModePill mode={t.mode} /></td>
                </tr>
              );
            }) : <tr><td colSpan={11} className="muted">No orders yet today.</td></tr>}
          </tbody>
        </table>
      </div>
      <h3 className="h" style={{ fontSize: 16, marginTop: 32 }}>History</h3>
      <p className="sub" style={{ marginBottom: 0 }}>One row per round trip: entry to exit, net of both legs' charges. R is the result in multiples of the risk at entry.</p>
      <History q={history} />
    </>
  );
}
