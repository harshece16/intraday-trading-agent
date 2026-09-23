import { downloadWithKey } from "../api";
import { clock, money, num, tone } from "../format";
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

export default function Trades({ state: s }) {
  const tax = s.tax || { turnover: 0, net_pnl: 0, gross_pnl: 0, charges: 0, closed_trades: 0 };
  const runningNet = runningNetById(s.trades);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
        <h2 className="h">Trade journal</h2>
        <button className="btn" onClick={() => downloadWithKey("/api/journal/trades.csv", "trader-sahab-trades.csv")}>
          Export full history (CSV)
        </button>
      </div>
      <p className="sub">Every order today and the reason it was placed. Export includes every trade ever logged
        (paper and live, marked by mode), not just today's — for your own records at filing time.</p>
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
          <thead><tr><th>Time</th><th>Stock</th><th>Action</th><th>Shares</th><th>Price</th><th>Invested</th><th>Charges</th><th>P&amp;L</th><th>Running net</th><th>Why</th><th>Mode</th></tr></thead>
          <tbody>
            {s.trades.length ? s.trades.map((t) => {
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
                  <td>{t.mode === "live" ? <span className="pill short">Live</span> : <span className="pill neutral">Paper</span>}</td>
                </tr>
              );
            }) : <tr><td colSpan={11} className="muted">No orders yet today.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
