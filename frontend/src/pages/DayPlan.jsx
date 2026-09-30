import { useState } from "react";
import { useApi } from "../api";
import LoadState from "../components/LoadState";
import { money, num, pct, tone, dateLabel, clock } from "../format";
import { SidePill } from "../components/Pill";

function PlanTable({ candidates }) {
  if (!candidates.length) return <p className="empty">No ranked candidates to size right now — check back once a scan has run.</p>;
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead>
          <tr>
            <th>Symbol</th><th>Side</th><th>LTP</th><th>Qty at this capital</th>
            <th>Stop</th><th>Target</th><th>Risk if stopped</th><th>Reward if it hits target</th><th>RRR</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr key={c.symbol} style={!c.tradable ? { opacity: 0.5 } : undefined}>
              <td>{c.symbol}</td>
              <td><SidePill side={c.side} /></td>
              <td>{num(c.ltp)}</td>
              <td>{c.tradable ? c.qty : "0 — too small to size a share"}</td>
              <td>{num(c.stop_price)}</td>
              <td>{num(c.target_price)}</td>
              <td className="down">{money(-c.risk_rupees)}</td>
              <td className="up">{money(c.reward_rupees)}</td>
              <td>{c.rrr != null ? `${c.rrr}:1` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {candidates.some((c) => c.side_basis !== "checklist") && (
        <p className="muted">The day's list sets no side. The side is the checklist's reading where it has read the stock;
          otherwise the long case is shown. A short has the same size and risk, with the stop and target mirrored.</p>
      )}
    </div>
  );
}

function OutcomeTrades({ trades }) {
  if (!trades.length) return <p className="empty">No fills yet today.</p>;
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Realized</th><th>R-multiple</th></tr></thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id}>
              <td>{clock(t.ts)}</td><td>{t.symbol}</td><td>{t.side}</td><td>{t.quantity}</td>
              <td>{num(t.price)}</td>
              <td className={tone(t.realized)}>{t.realized != null ? money(t.realized) : "—"}</td>
              <td>{t.r_multiple != null ? `${t.r_multiple.toFixed(2)}R` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function DayPlan() {
  const [capitalInput, setCapitalInput] = useState("5000");
  const [capital, setCapital] = useState(5000);
  const { data, error, reload } = useApi(`/api/day-plan?capital=${encodeURIComponent(capital)}`, 20000);

  function applyCapital() {
    const v = parseFloat(capitalInput);
    if (v > 0) setCapital(v);
  }

  if (!data) return <><h2 className="h">Day Plan</h2><LoadState error={error} onRetry={reload} /></>;
  const { plan: p, outcome: o } = data;

  return (
    <>
      <h2 className="h">Day Plan</h2>
      <p className="sub">
        What the risk model's own rules say a capital amount can actually do today, and — separately — what
        literally happened. Not a return forecast: there's no proven edge yet to base one on (the Dimaag Scorecard's
        Information Coefficient is currently negative), so an "expected P&amp;L" would be a made-up number. What's
        real instead: the exact ₹ risk/reward each current pick implies, and today's actual fills measured against
        the risk model's own limits — not against an invented target.
      </p>

      <div className="cardbox">
        <h2 className="h" style={{ fontSize: 16 }}>Your plan</h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center", margin: "8px 0 14px", flexWrap: "wrap" }}>
          <label htmlFor="capital-input" className="detail">Capital you're planning to trade with</label>
          <span>₹</span>
          <input
            id="capital-input" type="number" min="0" step="100" value={capitalInput}
            onChange={(e) => setCapitalInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applyCapital()}
            style={{ width: 110, padding: "6px 8px", background: "var(--panel-2, #1a1a24)", border: "1px solid var(--rule)", borderRadius: 6, color: "inherit" }}
          />
          <button className="btn" onClick={applyCapital}>Recalculate</button>
        </div>
        <div className="rb-row">
          <div className="rb-chip"><b>Max risk / trade (1%)</b><span>{money(p.max_risk_per_trade_rupees)}</span></div>
          <div className="rb-chip"><b>Max daily loss ({p.max_daily_loss_pct}%)</b><span>{money(p.max_daily_loss_rupees)}</span></div>
          <div className="rb-chip"><b>Max open positions</b><span>{p.max_open_positions}</span></div>
          <div className="rb-chip"><b>Tradable picks right now</b><span>{p.tradable_count} of {p.candidates.length}</span></div>
        </div>
        {p.source && <p className="detail" style={{ marginTop: 10 }}>Sized against {p.source}.</p>}
        {p.candidates.length > 0 && p.tradable_count === 0 && (
          <div className="tax" style={{ marginTop: 10 }}>
            ₹{num(p.capital, 0)} produces 0 shares for every current pick at 1% risk — the risk-per-trade in rupees
            is smaller than a single share's stop distance. Nothing would fire at this capital today; this isn't a
            bug, it's Van Tharp's Percent Risk Model doing what it's designed to do.
          </div>
        )}
        {p.exceeds_daily_loss_cap && p.tradable_count > 0 && (
          <div className="tax" style={{ marginTop: 10 }}>
            If every current pick got filled and every one hit its stop, that's {money(-p.total_risk_if_all_filled_rupees)} —
            more than the {money(p.max_daily_loss_rupees)} daily loss cap. In practice max_open_positions
            ({p.max_open_positions}) and the daily-loss circuit breaker stop that from actually happening.
          </div>
        )}
        <div style={{ marginTop: 12 }}>
          <PlanTable candidates={p.candidates} />
        </div>
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          Stop/target here use the ATR-based estimate (1.5× / 3× ATR); a live entry uses the full checklist's
          structural stop (pattern low/high, support/resistance), which can sit closer or further away.
        </p>
      </div>

      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>What actually happened today</h2>
        <p className="muted" style={{ margin: "0 0 10px", fontSize: 12.5 }}>
          {dateLabel(o.date)} — {o.mode === "paper" ? "paper" : "real"} fills only, sized against{" "}
          {o.mode === "paper" ? "the fixed paper-mode test capital" : "the account's real capital"} that day
          ({money(o.capital_used_today)}), not the hypothetical amount above.
        </p>
        <div className="rb-row">
          <div className="rb-chip"><b>Trades today</b><span>{o.trade_count}</span></div>
          <div className="rb-chip"><b>Realized P&amp;L</b><span className={tone(o.realized_pnl)}>{money(o.realized_pnl)}</span></div>
          <div className="rb-chip"><b>Win rate (closed)</b><span>{o.win_rate_pct != null ? `${o.win_rate_pct}%` : "not enough closed trades yet"}</span></div>
          <div className="rb-chip"><b>Stayed within daily loss cap</b><span className={o.hit_daily_loss_limit ? "down" : "up"}>{o.hit_daily_loss_limit ? `No — hit the ${money(o.max_daily_loss_rupees)} limit` : "Yes"}</span></div>
        </div>
        <div style={{ marginTop: 12 }}>
          <OutcomeTrades trades={o.trades} />
        </div>
      </div>
    </>
  );
}
