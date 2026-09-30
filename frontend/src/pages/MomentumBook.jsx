import { useApi } from "../api";
import LoadState from "../components/LoadState";
import { money, num, tone } from "../format";
import SymLink from "../components/SymLink";

const STATUS = {
  not_started: ["neutral", "Not started", "The first evening job hasn't run yet. It runs after 19:30 on trading days."],
  waiting_for_month_end: ["wait", "Waiting for month-end", "The book buys its first 15 names on the first session after a month-end close."],
  active: ["long", "Active (paper)", "Holding 15 names; rebalanced on the first session of each month."],
  switched_off: ["short", "Switched off", "The book fell below its pre-registered band and stopped itself."],
};

const WHY = { locked: "Locked at its price band", no_trade: "Did not trade" };
const SIDE = { BUY: ["up", "Bought"], SELL: ["down", "Sold"], "CANCELLED BUY": ["muted", "Buy cancelled"] };

// What the trade row should say beyond its figures: it waited, it was sold in
// trade-for-trade, or it was given up after five sessions.
function tradeNote(t) {
  const notes = [];
  if (t.side === "CANCELLED BUY") notes.push(`No fill in five sessions since ${t.ordered}`);
  else if (t.ordered) notes.push(`Waited since ${t.ordered}`);
  if (t.series) notes.push(`In trade-for-trade (${t.series})`);
  return notes.join(" · ") || "—";
}

function pctOf(x, d = 2) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`;
}

function NavChart({ nav }) {
  if (!nav || nav.length < 2) return <p className="empty">The value chart starts after the first rebalance.</p>;
  const b0 = nav[0].book, m0 = nav[0].bench;
  const book = nav.map((r) => (r.book / b0) * 100);
  const bench = nav.map((r) => (r.bench / m0) * 100);
  const lo = Math.min(...book, ...bench), hi = Math.max(...book, ...bench);
  const w = 640, h = 180, pad = 6;
  const x = (i) => pad + (i / (nav.length - 1)) * (w - 2 * pad);
  const y = (v) => h - pad - ((v - lo) / (hi - lo || 1)) * (h - 2 * pad);
  const path = (s) => s.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <figure style={{ margin: "8px 0 0" }}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Book value against its benchmark, both starting at 100">
        <path d={path(bench)} fill="none" stroke="var(--ink-2)" strokeWidth="1.5" strokeDasharray="4 3" />
        <path d={path(book)} fill="none" stroke="var(--long)" strokeWidth="2" />
      </svg>
      <figcaption className="muted" style={{ fontSize: 12 }}>
        Solid: the book. Dashed: its benchmark, the same 200 stocks equal-weighted. Both start at 100 on {nav[0].date}.
      </figcaption>
    </figure>
  );
}

export default function MomentumBook() {
  const { data, error, reload } = useApi("/api/momentum-book", 60000);
  if (!data) return <LoadState error={error} onRetry={reload} />;

  const [pillClass, label, blurb] = STATUS[data.status] || ["neutral", data.status, ""];
  const excess = data.cumulative_excess;
  const checks = data.data || {};           // the evening job's data checks (#159)
  const floor = data.band_floor;

  return (
    <>
      <h2 className="h">Momentum book <span className={`pill ${pillClass}`} style={{ verticalAlign: "middle" }}>{label}</span></h2>
      <p className="sub">
        The positional strategy that passed its pre-registered test (trial 120) and, narrowly, its re-run on
        repaired prices (trial 126): hold the 15 of NSE's 200 most-traded stocks with the strongest 6- and
        12-month momentum, in delivery, rebalanced monthly. <strong>Paper only</strong> — no order is placed.
        It is not a guarantee: momentum has losing years (−12% against its benchmark in 2025).
      </p>
      <p className="muted" style={{ marginTop: -8 }}>{data.status_reason || blurb}</p>
      {checks.problem && (
        <p className="down" role="alert" style={{ fontSize: 13 }}>
          The last evening run stopped early: {checks.problem}. Nothing past that day is traded or marked until the
          data is in.
        </p>
      )}

      <div className="grid3" style={{ margin: "16px 0" }}>
        <div className="stat"><small>Book value</small><strong>₹{num(data.book_value, 0)}</strong>
          <small className={tone(data.book_value - data.capital)}>{money(data.book_value - data.capital)} on ₹{num(data.capital, 0)}</small></div>
        <div className="stat"><small>Benchmark value</small><strong>₹{num(data.bench_value, 0)}</strong>
          <small className={tone(data.bench_value - data.capital)}>{money(data.bench_value - data.capital)}</small></div>
        <div className="stat"><small>Cumulative excess ({data.excess_months || 0} months)</small>
          <strong className={tone(excess)}>{pctOf(excess)}</strong>
          <small>{floor != null ? `Switch-off floor now ${pctOf(floor)}` : `Band applies from month ${data.band_from_month}`}</small></div>
      </div>

      <NavChart nav={data.nav} />

      <h3 style={{ marginTop: 24 }}>Holdings</h3>
      {data.holdings && data.holdings.length ? (
        <div className="table-wrap">
          <table className="datatable">
            <thead><tr><th>Stock</th><th>Held since</th><th>Invested</th><th>Fill price</th></tr></thead>
            <tbody>
              {data.holdings.map((h) => (
                <tr key={h.symbol}>
                  <td><SymLink sym={h.symbol} /></td><td>{h.since}</td>
                  <td>₹{num(h.invested, 0)}</td><td>{h.fill_price != null ? num(h.fill_price) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="empty">No holdings yet.</p>}

      {data.waiting_orders && data.waiting_orders.length ? (
        <>
          <h3 style={{ marginTop: 24 }}>Orders waiting</h3>
          <p className="muted" style={{ marginTop: -4 }}>
            An order is not filled on a day the stock closes locked at its price band or does not trade. It is tried
            again each session. A buy is given up after five sessions; a sell waits until it fills.
          </p>
          <div className="table-wrap">
            <table className="datatable">
              <thead><tr><th>Order</th><th>Stock</th><th>Ordered</th><th>Why it waits</th></tr></thead>
              <tbody>
                {data.waiting_orders.map((o) => (
                  <tr key={`${o.side}-${o.symbol}`}>
                    <td className={o.side === "BUY" ? "up" : "down"}>{o.side === "BUY" ? "Buy" : "Sell"}</td>
                    <td><SymLink sym={o.symbol} /></td><td>{o.ordered}</td>
                    <td>{WHY[o.reason] || "Not tried yet"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      <h3 style={{ marginTop: 24 }}>Recent trades</h3>
      {data.recent_trades && data.recent_trades.length ? (
        <div className="table-wrap">
          <table className="datatable">
            <thead><tr><th>Date</th><th>Side</th><th>Stock</th><th>Value</th><th>Charges and slippage</th><th>Note</th></tr></thead>
            <tbody>
              {[...data.recent_trades].reverse().map((t, i) => {
                const [cls, label] = SIDE[t.side] || ["muted", t.side];
                return (
                  <tr key={`${t.date}-${t.symbol}-${i}`}>
                    <td>{t.date}</td><td className={cls}>{label}</td>
                    <td><SymLink sym={t.symbol} /></td><td>₹{num(t.value, 0)}</td>
                    <td className="muted">{t.side === "CANCELLED BUY" ? "—" : `₹${num(t.cost, 2)}`}</td>
                    <td className="muted">{tradeNote(t)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : <p className="empty">No trades yet.</p>}

      <p className="muted" style={{ fontSize: 12, marginTop: 20 }}>
        Last session processed: {data.last_processed || "—"} · latest NSE file: {data.latest_session || "—"} · updated {data.updated_at || "—"}
        {" "}· corporate-actions file from {checks.corporate_actions_as_of ? checks.corporate_actions_as_of.replace("T", " ") : "—"}
        {checks.corporate_actions_refreshed === false && <span className="down"> (the last refresh failed)</span>}.
        Prices are NSE's daily bhavcopies, trade-for-trade rows included, adjusted with NSE's corporate-actions file.
        Fills are at the next session's close, unless the stock is locked at its band or did not trade.
        Rules and evidence: docs/research/results-3i-momentum-corrected-data.md and results-universe-width.md.
      </p>
    </>
  );
}
