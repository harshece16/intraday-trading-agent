import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { money, num, tone } from "../format";
import Tip from "../components/Tip";

function TrendTag({ trend }) {
  const cls = trend === "up" ? "long" : trend === "down" ? "short" : "neutral";
  const label = trend === "up" ? "Uptrend" : trend === "down" ? "Downtrend" : "Sideways";
  return <span className={`pill ${cls}`}>{label}</span>;
}

export default function PortfolioDiagnostic() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/api/portfolio/diagnostic");
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setData(await res.json());
    } catch (e) {
      setError(String(e.message || e));
    }
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  return (
    <>
      <h2 className="h">Holdings diagnostic</h2>
      <p className="sub">
        Today's technical read on your real Kite holdings — the same indicators the scanner runs on the NIFTY 100.
        This is deliberately <b>not</b> a buy/sell recommendation or a return forecast: it names what the chart shows
        today (<Tip k="ema20">trend</Tip>, <Tip k="rsi">RSI</Tip>, distance from 52-week levels, any confirmed daily
        pattern) and leaves the decision to you.
      </p>
      <div className="tax" style={{ marginBottom: 16 }}>
        This isn't advice from a SEBI-registered investment adviser. It reads your Kite holdings and describes each
        chart. The decision is yours.
      </div>
      {loading && <p className="empty"><span className="spinner" />Downloading a year of daily data for each holding… this can take a moment.</p>}
      {error && <div className="tax">Couldn't load the diagnostic: {error}. <button className="btn" onClick={load} style={{ marginLeft: 8 }}>Retry</button></div>}
      {data && (
        <>
          {data.unreadable?.length > 0 && (
            <p className="empty">Couldn't fetch daily data for: {data.unreadable.join(", ")}.</p>
          )}
          <div className="table-wrap">
            <table className="datatable">
              <thead>
                <tr><th>Symbol</th><th>Qty</th><th>P&amp;L</th><th>Close</th><th>Trend</th><th>RSI</th><th>52w high</th><th>52w low</th><th>Support</th><th>Resistance</th><th>Today's read</th></tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.symbol}>
                    <td>{r.symbol}</td>
                    <td>{r.quantity}</td>
                    <td className={tone(r.pnl)}>{money(r.pnl)}</td>
                    <td>{num(r.close)}</td>
                    <td><TrendTag trend={r.trend} /></td>
                    <td>{r.rsi ?? "—"}</td>
                    <td>{r.pct_from_52w_high != null ? `-${r.pct_from_52w_high}%` : "—"}</td>
                    <td>{r.pct_from_52w_low != null ? `+${r.pct_from_52w_low}%` : "—"}</td>
                    <td>{r.support ?? "—"}</td>
                    <td>{r.resistance ?? "—"}</td>
                    <td style={{ fontSize: 13 }}>
                      {r.posture.join("; ")}
                      {r.confirmed_patterns.length > 0 && <><br /><span className="muted">Confirmed: {r.confirmed_patterns.join(", ")}</span></>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
