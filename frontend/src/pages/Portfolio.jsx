import { Link } from "react-router-dom";
import { postJson, useAction, useApi } from "../api";
import LoadState from "../components/LoadState";
import { clockIST, inr, money, num, pct, tone } from "../format";
import { ConfidencePill } from "../components/Pill";

function PaperPositions({ positions }) {
  const rows = Object.entries(positions || {});
  if (!rows.length) return <p className="empty">No open positions right now.</p>;
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

function FnoSection({ q, toggle }) {
  const fno = q.data;
  if (!fno) return <LoadState error={q.error && `F&O status: ${q.error}`} onRetry={q.reload} label="Loading F&O status…" />;
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
        <button className={`btn ${fno.enabled ? "primary" : ""}`} disabled={toggle.busy} onClick={() => toggle.run(!fno.enabled)}>
          {toggle.busy ? "Switching…" : fno.enabled ? "Turn F&O off" : "Turn F&O on"}
        </button>
        {toggle.error && <p className="down" role="alert" style={{ margin: "8px 0 0", fontSize: 13 }}>Couldn't switch F&amp;O: {toggle.error}.</p>}
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
      {fno.kite_connected && <PcrSection />}
    </>
  );
}

function PcrSection() {
  // Context only, so a failed load just leaves the panel out.
  const { data: pcr } = useApi("/api/fno/pcr", 30000);
  if (!pcr || pcr.error) return null;
  const entries = Object.entries(pcr).filter(([, v]) => v && !v.error);
  if (!entries.length) return null;
  return (
    <div className="cardbox" style={{ marginTop: 16 }}>
      <h2 className="h" style={{ fontSize: 16 }}>Options positioning (Put/Call OI ratio)</h2>
      <p className="muted" style={{ margin: "0 0 10px", fontSize: 12.5 }}>
        Real open-interest data, near-the-money strikes only — a widely-used practitioner heuristic, not rigorously
        backtested evidence. Context, not a signal: never feeds the confidence score.
      </p>
      <div className="rb-row">
        {entries.map(([underlying, d]) => (
          <div className="rb-chip" key={underlying}>
            <b>{underlying}</b>
            <span>PCR {d.pcr} — {d.reading}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Portfolio({ state: s }) {
  const portfolioQ = useApi("/api/portfolio");
  const fnoQ = useApi("/api/fno/status");
  const p = portfolioQ.data;

  // The switch used to fail silently and just reload the old value (#236).
  const fnoToggle = useAction(async (enabled) => {
    if (enabled && !confirm("Turn F&O on? Combined with Live mode, this lets Trader Sahab buy real option contracts " +
        "with real premium at risk, sized and confidence-gated automatically — no per-trade confirmation. " +
        "Paper mode still simulates it safely either way.")) return;
    try {
      await postJson("/api/fno/enable", { enabled });
    } finally {
      fnoQ.reload();
    }
  });

  if (!p) return <LoadState error={portfolioQ.error} onRetry={portfolioQ.reload} label="Loading portfolio…" />;
  const eq = (p.margins || {}).equity || {};
  const av = eq.available || {};
  const ut = eq.utilised || {};

  return (
    <>
      <h2 className="h">Portfolio</h2>
      <p className="sub">What the account holds right now, F&amp;O settings, and today's P&amp;L.</p>
      {p.error && <div className="tax" role="alert">{p.error}</div>}
      {p.kite_connected && p.margins ? (
        <>
          <div className="cardbox">
            <h2 className="h" style={{ fontSize: 16 }}>Kite margins (equity segment)</h2>
            <div className="rb-row">
              <div className="rb-chip"><b>Cash</b><span>{inr(av.cash || 0)}</span></div>
              <div className="rb-chip"><b>Live balance</b><span>{inr(av.live_balance ?? av.cash ?? 0)}</span></div>
              <div className="rb-chip"><b>Intraday payin</b><span>{inr(av.intraday_payin || 0)}</span></div>
              <div className="rb-chip"><b>Collateral</b><span>{inr(av.collateral || 0)}</span></div>
            </div>
            <div className="detail" style={{ margin: "10px 0 4px" }}>Utilised (what's tied up right now)</div>
            <div className="rb-row">
              <div className="rb-chip"><b>Debits</b><span>{inr(ut.debits || 0)}</span></div>
              <div className="rb-chip"><b>Span</b><span>{inr(ut.span || 0)}</span></div>
              <div className="rb-chip"><b>Exposure</b><span>{inr(ut.exposure || 0)}</span></div>
              <div className="rb-chip"><b>Option premium</b><span>{inr(ut.option_premium || 0)}</span></div>
              <div className="rb-chip"><b>M2M unrealised</b><span className={tone(ut.m2m_unrealised)}>{money(ut.m2m_unrealised || 0)}</span></div>
              <div className="rb-chip"><b>Holding sales</b><span>{inr(ut.holding_sales || 0)}</span></div>
            </div>
            <div className="detail" style={{ marginTop: 10 }}>
              {!p.sync_capital_with_kite ? (
                <>Risk-model capital is pinned in config, not synced to this live balance (config.RISK.sync_capital_with_kite is off).</>
              ) : s?.paper_mode ? (
                <>
                  <b>Paper mode</b> is sizing against a fixed {inr(p.risk_total_capital)} test figure
                  (config.RISK.paper_capital), <i>not</i> this live balance — set up so simulated trades actually get
                  sized realistically. Going live snaps sizing back to this real balance immediately.
                </>
              ) : (
                <>
                  Risk-model capital is synced to this live balance — <b>{inr(p.risk_total_capital)}</b>, last
                  synced {p.capital_sync ? clockIST(p.capital_sync.synced_at) : "not yet"}.
                  Position sizing (Van Tharp 1% rule) uses the real number here, not a config guess, so live orders
                  are sized on the current balance, not a stale figure.
                </>
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
        <div className="tax">Kite isn't connected, so this page shows only the engine's paper positions. Click Connect Kite in the top bar to see your holdings and margins.</div>
      )}
      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>Today's open positions ({s ? (s.paper_mode ? "paper" : "live") : "engine"})</h2>
        <PaperPositions positions={p.paper_positions} />
      </div>
      <div style={{ marginTop: 16 }}><FnoSection q={fnoQ} toggle={fnoToggle} /></div>
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
