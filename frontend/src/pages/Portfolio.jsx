import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch, apiJson } from "../api";
import { money, num, pct, tone } from "../format";
import { ConfidencePill } from "../components/Pill";

function PaperPositions({ positions }) {
  const rows = Object.entries(positions || {});
  if (!rows.length) return <p className="empty">No open paper/live positions right now.</p>;
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead><tr><th>Symbol</th><th>Qty</th><th>Avg price</th><th>LTP</th><th>Unrealized</th><th>Stop</th><th>Target</th></tr></thead>
        <tbody>
          {rows.map(([sym, p]) => (
            <tr key={sym}>
              <td>{sym}</td>
              <td className={p.quantity > 0 ? "up" : "down"}>{p.quantity > 0 ? "LONG" : "SHORT"} {Math.abs(p.quantity)}</td>
              <td>{num(p.avg_price)}</td><td>{p.ltp != null ? num(p.ltp) : "—"}</td>
              <td className={tone(p.unrealized_pnl)}>{p.unrealized_pnl != null ? money(p.unrealized_pnl) : "—"}</td>
              <td>{p.stop_price != null ? num(p.stop_price) : "—"}</td>
              <td>{p.target_price != null ? num(p.target_price) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KiteHoldings({ holdings }) {
  if (!holdings || !holdings.length) return <p className="empty">No T+1 settled holdings in this Kite account.</p>;
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead><tr><th>Symbol</th><th>Qty</th><th>Avg cost</th><th>LTP</th><th>P&amp;L</th><th>P&amp;L %</th></tr></thead>
        <tbody>
          {holdings.map((h) => {
            const pnlPct = h.average_price ? ((h.last_price - h.average_price) / h.average_price) * 100 : 0;
            return (
              <tr key={h.tradingsymbol}>
                <td>{h.tradingsymbol}</td><td>{h.quantity}</td><td>{num(h.average_price)}</td>
                <td>{num(h.last_price)}</td><td className={tone(h.pnl)}>{money(h.pnl)}</td>
                <td className={tone(pnlPct)}>{pct(pnlPct)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function FnoSection({ fno, onToggle }) {
  if (!fno) return <p className="empty">Loading F&amp;O status…</p>;
  const positions = Object.entries(fno.open_positions || {});
  return (
    <>
      <div className="cardbox">
        <h2 className="h" style={{ fontSize: 16 }}>F&amp;O (options-buying only)</h2>
        <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>
          Buys calls on a LONG signal, puts on a SHORT signal — never writes/sells options or trades futures (see the
          Technical Analysis page for why). A separate switch from Paper/Live: an order only reaches Kite when both this
          is ON and the header says Live.
        </p>
        <div className="rb-row" style={{ marginBottom: 12 }}>
          <div className="rb-chip"><b>Capital ring-fenced</b><span>₹{num(fno.capital, 0)}</span></div>
          <div className="rb-chip"><b>Max premium risk/trade</b><span>{fno.max_premium_risk_pct}%</span></div>
          <div className="rb-chip"><b>Confidence bar to trade</b><span>{fno.min_confidence_to_trade}/100</span></div>
        </div>
        <button className={`btn ${fno.enabled ? "primary" : ""}`} onClick={() => onToggle(!fno.enabled)}>
          {fno.enabled ? "F&O is ON — turn off" : "Turn F&O on"}
        </button>
        {!fno.kite_connected && <p className="empty" style={{ marginTop: 8 }}>Kite isn't connected — F&amp;O needs it for live option quotes and contract data even in paper mode.</p>}
      </div>
      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>Open F&amp;O positions</h2>
        {!positions.length ? (
          <p className="empty">No open option positions.</p>
        ) : (
          positions.map(([underlying, pos]) => (
            <div style={{ padding: "10px 0", borderBottom: "1px solid var(--rule)" }} key={underlying}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
                <b>{pos.tradingsymbol}</b>
                {pos.confidence && <ConfidencePill score={pos.confidence.score} />}
              </div>
              <div className="detail" style={{ marginTop: 4 }}>
                {pos.lots} lot(s) of {pos.lot_size} × entry premium {num(pos.entry_premium)}, now {num(pos.ltp)}{" "}
                <span className={tone(pos.unrealized_pnl)}>({money(pos.unrealized_pnl)})</span>. Stop {num(pos.stop_premium)}, target {num(pos.target_premium)}.
                Max loss was capped at ₹{num(pos.max_loss, 0)}.
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
}

export default function Portfolio({ state: s }) {
  const [p, setP] = useState(null);
  const [fno, setFno] = useState(null);

  async function refresh() {
    try { setP(await apiJson("/api/portfolio")); } catch (e) {}
    try { setFno(await apiJson("/api/fno/status")); } catch (e) {}
  }

  useEffect(() => { refresh(); }, []);

  async function toggleFno(enabled) {
    if (enabled && !confirm("Turn F&O on? Combined with Live mode, this lets Trader Sahab buy real option contracts " +
        "with real premium at risk, sized and confidence-gated automatically — no per-trade confirmation. " +
        "Paper mode still simulates it safely either way.")) return;
    try {
      await apiFetch("/api/fno/enable", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
    } catch (e) {}
    refresh();
  }

  if (!p) return <p className="empty">Loading portfolio…</p>;

  return (
    <>
      {p.error && <div className="tax">{p.error}</div>}
      {p.kite_connected && p.margins ? (
        <>
          <div className="cardbox">
            <h2 className="h" style={{ fontSize: 16 }}>Kite margins (equity segment)</h2>
            <div className="rb-row">
              <div className="rb-chip"><b>Cash</b><span>{money((p.margins.equity || {}).available?.cash || 0)}</span></div>
              <div className="rb-chip"><b>Live balance</b><span>{money((p.margins.equity || {}).available?.live_balance ?? (p.margins.equity || {}).available?.cash ?? 0)}</span></div>
              <div className="rb-chip"><b>Intraday payin</b><span>{money((p.margins.equity || {}).available?.intraday_payin || 0)}</span></div>
              <div className="rb-chip"><b>Collateral</b><span>{money((p.margins.equity || {}).available?.collateral || 0)}</span></div>
            </div>
            <div className="detail" style={{ margin: "10px 0 4px" }}>Utilised (what's tied up right now)</div>
            <div className="rb-row">
              <div className="rb-chip"><b>Debits</b><span>{money((p.margins.equity || {}).utilised?.debits || 0)}</span></div>
              <div className="rb-chip"><b>Span</b><span>{money((p.margins.equity || {}).utilised?.span || 0)}</span></div>
              <div className="rb-chip"><b>Exposure</b><span>{money((p.margins.equity || {}).utilised?.exposure || 0)}</span></div>
              <div className="rb-chip"><b>Option premium</b><span>{money((p.margins.equity || {}).utilised?.option_premium || 0)}</span></div>
              <div className="rb-chip"><b>M2M unrealised</b><span className={tone((p.margins.equity || {}).utilised?.m2m_unrealised)}>{money((p.margins.equity || {}).utilised?.m2m_unrealised || 0)}</span></div>
              <div className="rb-chip"><b>Holding sales</b><span>{money((p.margins.equity || {}).utilised?.holding_sales || 0)}</span></div>
            </div>
            <div className="detail" style={{ marginTop: 10 }}>
              {p.sync_capital_with_kite ? (
                <>
                  Risk-model capital is synced to this live balance — <b>{money(p.risk_total_capital)}</b>, last
                  synced {p.capital_sync ? new Date(p.capital_sync.synced_at * 1000).toLocaleTimeString() : "not yet"}.
                  Position sizing (Van Tharp 1% rule) always uses the real number here, not a config guess, so a
                  live order never gets rejected by Kite for insufficient margin against a stale figure.
                </>
              ) : (
                <>Risk-model capital is pinned in config, not synced to this live balance (config.RISK.sync_capital_with_kite is off).</>
              )}
            </div>
          </div>
          <div className="cardbox" style={{ marginTop: 16 }}>
            <h2 className="h" style={{ fontSize: 16 }}>Kite holdings</h2>
            <KiteHoldings holdings={p.holdings} />
            <Link className="more" to="/portfolio/diagnostic" style={{ display: "inline-block", marginTop: 10 }}>
              Run today's technical diagnostic on these holdings →
            </Link>
          </div>
        </>
      ) : (
        <div className="tax">Kite isn't connected, so this shows today's paper positions only. Click "Connect" in the header to see real holdings and margins once you go live.</div>
      )}
      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>Today's open positions ({p.kite_connected ? "live" : "paper"})</h2>
        <PaperPositions positions={p.paper_positions} />
      </div>
      <div style={{ marginTop: 16 }}><FnoSection fno={fno} onToggle={toggleFno} /></div>
      {s && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>Today's P&amp;L</h2>
          <div className="rb-row">
            <div className="rb-chip"><b>Realized</b><span className={tone(s.realized_pnl_today)}>{money(s.realized_pnl_today)}</span></div>
            <div className="rb-chip"><b>Unrealized</b><span className={tone(s.unrealized_pnl)}>{money(s.unrealized_pnl)}</span></div>
          </div>
        </div>
      )}
    </>
  );
}
