import { useEffect, useState } from "react";
import { apiJson, useApi } from "../api";
import LoadState from "../components/LoadState";
import { num, signed, clock } from "../format";
import { StatusPill, ConfidencePill } from "../components/Pill";

function fmtWhen(ts) {
  if (!ts) return "—";
  const days = Math.floor((Date.now() / 1000 - ts) / 86400);
  return days < 1 ? "today" : days === 1 ? "1 day ago" : `${days} days ago`;
}

export default function Journal() {
  const { data: j, error, reload } = useApi("/api/journal/summary");
  const [fj, setFj] = useState(null);
  // undefined = still loading, null = fetch failed, array = loaded — kept distinct so a
  // failed fetch never renders the same "nothing to report" message as a genuine empty list.
  const [blocked, setBlocked] = useState(undefined);
  const [blockerStats, setBlockerStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    apiJson("/api/fno/journal").then((d) => !cancelled && setFj(d)).catch(() => {});
    apiJson("/api/journal/blocked-signals?hours=24&limit=50").then((d) => !cancelled && setBlocked(d)).catch(() => !cancelled && setBlocked(null));
    apiJson("/api/journal/blocker-stats?hours=24").then((d) => !cancelled && setBlockerStats(d)).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <h2 className="h">Sahab's Journal</h2>
      <p className="sub">The knowledge base built from every scan, checklist read and fill.</p>
      {!j ? (
        <LoadState error={error} onRetry={reload} label="Loading Sahab's Journal…" />
      ) : (
        <JournalBody j={j} fj={fj} blocked={blocked} blockerStats={blockerStats} />
      )}
    </>
  );
}

function JournalBody({ j, fj, blocked, blockerStats }) {
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

      {blockerStats && blockerStats.total_evaluations > 0 && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>Confidence gate — why signals get blocked</h2>
          <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>
            {blockerStats.total_evaluations} checklist reads in the last {blockerStats.window_hours}h. Near misses
            below are evaluations where exactly one required item was the sole blocker — the closest calls to a
            real trade. A setup clearing the checklist still has to pass the confidence gate (table below) before
            it trades.
          </p>
          {Object.keys(blockerStats.near_misses_by_lone_blocker || {}).length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
              {Object.entries(blockerStats.near_misses_by_lone_blocker)
                .sort((a, b) => b[1] - a[1])
                .map(([key, n]) => (
                  <span className="pill neutral" key={key}>{key}: {n} near-miss{n > 1 ? "es" : ""}</span>
                ))}
            </div>
          )}
          {blockerStats.rrr_distribution && (
            <p className="detail" style={{ margin: "0 0 12px" }}>
              Reward-to-risk of evaluated setups: median {blockerStats.rrr_distribution.median}, only{" "}
              {blockerStats.rrr_distribution.pct_at_or_above_1_5}% cleared the 1.5 bar Varsity requires.
            </p>
          )}

          {blocked === undefined ? (
            <p className="empty">Loading blocked signals…</p>
          ) : blocked === null ? (
            <p className="empty">Couldn't load blocked signals right now — try reloading the page.</p>
          ) : blocked.length > 0 ? (
            <div className="table-wrap">
              <table className="datatable">
                <thead>
                  <tr><th>Time</th><th>Symbol</th><th>Setup</th><th>Confidence</th><th>Why blocked</th></tr>
                </thead>
                <tbody>
                  {blocked.map((b, i) => (
                    <tr key={i}>
                      <td>{clock(b.ts)}</td>
                      <td>{b.symbol}</td>
                      <td>{b.setup || "—"}</td>
                      <td>{b.reason_type === "confidence_gate" ? <ConfidencePill score={b.final_score} /> : "—"}</td>
                      <td className="detail">
                        {b.reason_type === "confidence_gate"
                          ? `Local setup ${b.local_setup_score}/100 × ${b.system_multiplier.toFixed(2)}x system-evidence = ${b.final_score}/100 (needs ${b.min_confidence_bar}). ${b.system_multiplier_reason}`
                          : b.reason}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty">No blocked signals in this window — either nothing cleared the checklist, or everything that did also cleared the confidence gate.</p>
          )}
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
          <p style={{ margin: "0 0 4px" }}>{ic.ic != null ? `Mean daily Information Coefficient ${signed(ic.ic, 3)} across ${ic.sessions} separate sessions (t-stat ${ic.t_stat != null ? signed(ic.t_stat, 2) : "n/a"})` : `Not enough data yet — ${ic.sessions ?? 0} of ${ic.min_sessions ?? 20} sessions needed`}</p>
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
