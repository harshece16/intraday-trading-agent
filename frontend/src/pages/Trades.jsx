import { clock, money, num, tone } from "../format";
import { REASON_TEXT, tradeAction } from "../helpers";
import SymLink from "../components/SymLink";

export default function Trades({ state: s }) {
  const tax = s.tax || { turnover: 0, net_pnl: 0, charges: 0, closed_trades: 0 };

  return (
    <>
      <h2 className="h">Trade journal</h2>
      <p className="sub">Every order today and the reason it was placed.</p>
      <div className="tax">
        Intraday equity counts as <strong>speculative business income</strong>. So far: turnover <strong>₹{num(tax.turnover, 0)}</strong>{" "}
        (each closed trade's profit or loss, added up without signs), net P&amp;L <strong className={tone(tax.net_pnl)}>{money(tax.net_pnl)}</strong>, estimated
        charges <strong>₹{num(tax.charges, 0)}</strong>. Speculative losses only offset speculative gains and carry forward 4 years.
        Advance tax is due by 15 Jun, 15 Sep, 15 Dec and 15 Mar. Source: Zerodha Varsity, Markets and Taxation; check with a CA.
      </div>
      <div className="table-wrap" style={{ marginTop: 16 }}>
        <table className="datatable">
          <thead><tr><th>Time</th><th>Stock</th><th>Action</th><th>Shares</th><th>Price</th><th>Why</th><th>Mode</th></tr></thead>
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
                  <td>{[reason, t.note].filter(Boolean).join(": ") || "—"}</td>
                  <td>{t.mode === "live" ? <span className="pill short">Live</span> : <span className="pill neutral">Paper</span>}</td>
                </tr>
              );
            }) : <tr><td colSpan={7} className="muted">No orders yet today.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
