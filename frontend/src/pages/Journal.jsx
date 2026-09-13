import { useEffect, useState } from "react";
import { apiJson } from "../api";
import { num, signed } from "../format";
import { StatusPill } from "../components/Pill";

function fmtWhen(ts) {
  if (!ts) return "—";
  const days = Math.floor((Date.now() / 1000 - ts) / 86400);
  return days < 1 ? "today" : days === 1 ? "1 day ago" : `${days} days ago`;
}

export default function Journal() {
  const [j, setJ] = useState(null);
  const [fj, setFj] = useState(null);

  useEffect(() => {
    let cancelled = false;
    apiJson("/api/journal/summary").then((d) => !cancelled && setJ(d)).catch(() => {});
    apiJson("/api/fno/journal").then((d) => !cancelled && setFj(d)).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <h2 className="h">Sahab's Journal</h2>
      <p className="sub">The knowledge base built from every scan, checklist read and fill.</p>
      {!j ? (
        <p className="empty">Loading Sahab's Journal…</p>
      ) : (
        <JournalBody j={j} fj={fj} />
      )}
    </>
  );
}

function JournalBody({ j, fj }) {
  const ts = j.trade_stats || {};
  const scorecard = j.scorecard || [];
  const breakdown = Object.entries(j.checklist_item_breakdown || {});
  const ic = j.factor_ic;

  return (
    <>
      <div className="tax">
        Every scan and every checklist read — not just executed trades — is saved to a local database
        (backend/data/sahab_journal.db) so it survives a restart and builds into a knowledge base over time.
        <div className="detail" style={{ marginTop: 6 }}>
          {num(j.scans_logged, 0)} scans · {num(j.checklist_evals_logged, 0)} checklist reads · {num(j.trades_logged, 0)} fills logged, since {fmtWhen(j.logging_since)}.
        </div>
      </div>

      {scorecard.length > 0 && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>Dimaag Scorecard</h2>
          <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>
            Not a single made-up "IQ" — no such validated measure exists for a trading system. Each row below is
            graded against a bar already used elsewhere in this codebase, computed from real logged data, and says
            "not enough data yet" rather than guessing.
          </p>
          {scorecard.map((r, i) => (
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline", marginBottom: 10 }} key={i}>
              <div style={{ flex: 1 }}><b style={{ fontSize: 13.5 }}>{r.criterion}</b><div className="detail" style={{ marginTop: 2 }}>{r.detail}</div></div>
              <StatusPill status={r.status} />
            </div>
          ))}
        </div>
      )}

      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>What "good" actually looks like here</h2>
        <p style={{ margin: "0 0 4px", fontSize: 13 }}>
          SEBI's own study (released 24 Jul 2024, covering FY23) found <b>71% of individual intraday traders in the equity
          cash segment made a net loss</b> — rising to <b>80%</b> among those who traded more than 500 times a year.
          Loss-makers spent an extra 57% of their losses on trading costs alone; profit-makers spent only 19% of their
          profits on costs.
        </p>
        <p className="muted" style={{ margin: 0, fontSize: 13 }}>
          We can't honestly promise a ₹ target — nobody can, and anyone who does is guessing. The realistic bar this
          data sets: most traders like this lose, and the ones who don't are usually the ones costs eat least. So the
          goal for this paper-trading week isn't a return number — it's a positive expectancy (Dimaag Scorecard, above)
          at a trade frequency where costs don't eat the edge, before a single rupee goes live.
        </p>
      </div>

      {ts.closed_trades ? (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>Trade record</h2>
          <p style={{ margin: "0 0 4px" }}>{ts.closed_trades} closed trade{ts.closed_trades > 1 ? "s" : ""}, {ts.win_rate_pct}% won</p>
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>
            Expectancy {signed(ts.expectancy_r, 2)}R per trade (avg win {signed(ts.avg_win_r, 2)}R, avg loss {signed(ts.avg_loss_r, 2)}R).
            Kelly fraction {ts.kelly_pct == null ? "—" : ts.kelly_pct + "%"}{ts.kelly_pct != null && ts.kelly_pct <= 0 ? " — no edge yet, the right bet size is zero" : ""}.
          </p>
        </div>
      ) : (
        <p className="empty">No closed trades yet — nothing to score. This fills in once Sahab's Dimaag actually trades.</p>
      )}

      {breakdown.length > 0 && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>Which checklist rules actually matter</h2>
          <p className="muted" style={{ margin: "0 0 8px", fontSize: 13 }}>Average R-multiple of closed trades where each rule passed vs failed at entry.</p>
          <div className="table-wrap">
            <table className="datatable">
              <thead><tr><th>Rule</th><th>Pass</th><th>Fail</th></tr></thead>
              <tbody>
                {breakdown.map(([key, b]) => (
                  <tr key={key}>
                    <td>{key}</td>
                    <td className={b.pass.avg_r > 0 ? "up" : b.pass.avg_r < 0 ? "down" : ""}>{b.pass.n ? `${signed(b.pass.avg_r, 2)}R (${b.pass.n})` : "—"}</td>
                    <td className={b.fail.avg_r > 0 ? "up" : b.fail.avg_r < 0 ? "down" : ""}>{b.fail.n ? `${signed(b.fail.avg_r, 2)}R (${b.fail.n})` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {ic && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>Does the scan score predict the next move?</h2>
          <p style={{ margin: "0 0 4px" }}>{ic.ic != null ? `Information Coefficient ${signed(ic.ic, 3)} across ${ic.pairs} session pairs` : "Not enough data yet"}</p>
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>
            {ic.note || ""}{ic.ic == null ? "" : " (ML4Trading ch 1: rank correlation between today's score and the next session's move — 0 is no predictive power, ±1 is perfect)."}
          </p>
        </div>
      )}

      {fj && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>F&amp;O knowledge base</h2>
          <p style={{ margin: "0 0 4px" }}>
            {num(fj.evaluations_logged, 0)} confidence reads logged, {num(fj.trades_opened, 0)} trades opened, {num(fj.closed_trades, 0)} closed
            {fj.win_rate_pct != null ? ` (${fj.win_rate_pct}% won, expectancy ${signed(fj.expectancy_r, 2)}R)` : ""}.
          </p>
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>
            {fj.confidence_ic != null ? `Confidence-to-outcome rank correlation ${signed(fj.confidence_ic, 3)} ` : ""}{fj.confidence_ic_note || ""}
          </p>
        </div>
      )}
    </>
  );
}
