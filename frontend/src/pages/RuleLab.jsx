import { useApi } from "../api";
import LoadState from "../components/LoadState";
import { num, tone } from "../format";

// The single-rule paper lab (README section 124): 20 small rules, each with its
// own shadow paper book on the day's list. No orders; nothing that trades reads it.

const STATUS = {
  collecting: ["neutral", "Collecting"],
  screen_failed: ["short", "Screen failed"],
  candidate: ["wait", "Candidate"],
  confirmation_failed: ["short", "Confirmation failed"],
  confirmed: ["long", "Confirmed"],
};

function bp(x, d = 1) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : "−"}${Math.abs(Number(x)).toFixed(d)}`;
}

function rate(x) {
  return x === null || x === undefined ? "—" : `${(x * 100).toFixed(0)}%`;
}

function interval(ci) {
  return ci ? `${bp(ci[0], 0)} to ${bp(ci[1], 0)}` : "—";
}

function StatusCell({ row }) {
  const [cls, label] = STATUS[row.status] || STATUS.collecting;
  const route = row.route === "historical" ? " (historical)" : "";
  // Amendment 6: a rule below a look's floor is void at that look; it neither passes nor sets the bar.
  const look = row.status === "confirmation_failed" ? row.confirmation : row.status === "screen_failed" ? row.screen : null;
  if (look && look.void) return <span className="pill neutral">void (below the floor)</span>;
  return <span className={`pill ${cls}`}>{label}{row.status === "candidate" ? route : ""}</span>;
}

function LookNote({ rows, which, cohort }) {
  // Amendment 6: each look's critical value and the rules that actually set the bar, one line per cohort.
  const looked = rows.filter((r) => r.cohort === cohort).map((r) => r[which]).filter(Boolean);
  if (!looked.length) return null;
  const s = looked[0];
  const voided = looked.filter((x) => x.void).length;
  return (
    <p className="muted" style={{ fontSize: 12 }}>
      {which === "screen" ? "Screen" : "Confirmation"}, cohort {cohort}: {s.family_in_max} of {s.family} rules set the bar
      {voided ? ` (${voided} of this cohort void, below the floor)` : ""}; critical t {s.critical != null ? s.critical.toFixed(2) : "—"}.
    </p>
  );
}

function RuleTable({ rows }) {
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead>
          <tr>
            <th>Rule</th><th>Side</th><th>Trades</th><th>Win rate</th><th>Break-even</th>
            <th>Net bp a trade</th><th>95% interval</th><th>t</th><th>Net R</th><th>Losing run</th>
            <th>Historical bp</th><th>Decay</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.rule}>
              <td><strong>{r.rule}</strong> {r.name}</td>
              <td className={r.side === "LONG" ? "up" : "down"}>{r.side === "LONG" ? "Long" : "Short"}</td>
              <td>{r.n}{r.open ? <span className="muted"> +{r.open} open</span> : ""}</td>
              <td>{rate(r.win_rate)}</td>
              <td className="muted">{rate(r.break_even_win_rate)}</td>
              <td className={tone(r.mean)}>{bp(r.mean)}</td>
              <td className="muted">{interval(r.ci)}</td>
              <td>{r.t != null ? r.t.toFixed(2) : "—"}</td>
              <td className={tone(r.expectancy_r)}>{r.r_based ? (r.expectancy_r != null ? `${r.expectancy_r >= 0 ? "+" : "−"}${Math.abs(r.expectancy_r).toFixed(2)}R` : "—") : ""}</td>
              <td>{r.n ? r.max_consecutive_losses : "—"}</td>
              <td className={tone(r.historical && r.historical.mean)}>{r.historical ? bp(r.historical.mean) : "—"}</td>
              <td className={tone(r.decay_bp)}>{r.decay_bp != null ? bp(r.decay_bp) : "—"}</td>
              <td><StatusCell row={r} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function RuleLab() {
  const { data, error, reload } = useApi("/api/rule-lab", 60000);
  if (!data) return <LoadState error={error} onRetry={reload} />;
  const rows = data.rules || [];
  const cohort1 = rows.filter((r) => r.cohort === 1);
  const cohort2 = rows.filter((r) => r.cohort !== 1);
  const screenLeft = Math.max(0, data.screen_at - data.sessions);
  const anyTrades = rows.some((r) => r.n > 0 || r.open > 0);

  return (
    <>
      <h2 className="h">Rule lab <span className="pill neutral" style={{ verticalAlign: "middle" }}>Paper only</span></h2>
      <p className="sub">
        Each of {rows.length} small rules runs its own paper book on the day's list: {cohort1.length} of the lab's own
        (a candlestick pattern, a volume spike on an up or down bar, a trend turn, an opening-range break, a gap, a
        pullback to the 20-bar average) and {cohort2.length} taken from popular YouTube trading videos and named
        traders' published rules (5-EMA, VWAP bounce, CPR and pivots, Supertrend, MACD, Stoch RSI, squeeze and more).
        On every finished 5-minute bar a rule that fires buys or shorts ₹{num(data.notional, 0)} at the next bar's
        open and closes {data.hold_minutes} minutes later, or by the 15:05 bar; the two pullback rules use a stop
        beyond the signal bar and a 3R target instead. No stops otherwise. Every trade pays about{" "}
        {num(data.round_trip_bp, 1)} bp of Zerodha charges and slippage. <strong>No orders are placed</strong>, and
        nothing here changes the engine's trades, risk or review queue.
      </p>
      <p className="muted">
        The rules and the test were fixed in advance (<code>{data.prereg}</code>). Nothing is judged before the
        look: after {data.screen_at} lab sessions, every rule is tested once, with a correction for testing
        {" "}{rows.length} rules at once (the lab's own rules at a 2.5% error rate, the catalog rules at 1.25%); a rule that passes becomes a candidate and must pass again on the next{" "}
        {data.confirm_sessions} sessions. Only then can it be proposed to you, and going live needs your yes and the
        engine's own live gate. <strong>Earlier tests of rules like these lost money after costs</strong> (the
        combination search, trials 128–202; the confluence engine, trial 40).
      </p>

      <div className="grid3" style={{ margin: "16px 0" }}>
        <div className="stat"><small>Lab sessions</small>
          <strong>{data.sessions}</strong>
          <small>{data.first_session ? `${data.first_session} to ${data.last_session}` : "the first one is the next trading day"}</small></div>
        <div className="stat"><small>The screen</small>
          <strong>{screenLeft ? `in ${screenLeft} sessions` : "done"}</strong>
          <small>{screenLeft ? `after session ${data.screen_at}` : `read once, after session ${data.screen_at}`}; a rule needs at least {data.screen_min_trades} trades</small></div>
        <div className="stat"><small>Historical search (2024–25)</small>
          <strong>{data.historical_run ? "run" : "not run yet"}</strong>
          <small>{data.historical_run ? "its figures are beside each rule" : "waiting for an independent review"}</small></div>
      </div>

      <p className="muted" style={{ fontSize: 12 }}>
        <strong>A short record says little.</strong> With a few dozen trades, a rule's average can be +20 bp or −20 bp
        by luck alone; the interval shows how wide that is. The running figures below are not a test.
      </p>

      {!anyTrades && <p className="empty">No paper trade yet. The lab starts with the first session after it is deployed.</p>}
      <h3 style={{ marginTop: 20 }}>The lab's own rules</h3>
      <LookNote rows={rows} which="screen" cohort={1} />
      <LookNote rows={rows} which="confirmation" cohort={1} />
      <RuleTable rows={cohort1} />
      <h3 style={{ marginTop: 24 }}>Rules from the strategy catalogs (YouTube and named traders)</h3>
      <p className="muted" style={{ fontSize: 12 }}>
        Each traded with the lab's exits (30 minutes, or a stop beyond the signal bar and a 3R target), not the
        video's own. Rules this project had already tested and found losing were left out.
      </p>
      <LookNote rows={rows} which="screen" cohort={2} />
      <LookNote rows={rows} which="confirmation" cohort={2} />
      <RuleTable rows={cohort2} />
      <p className="muted" style={{ fontSize: 12 }}>
        Net bp is after charges and slippage. Break-even is the win rate this rule's average win and loss would need
        to make nothing. Net R is for the two pullback rules only (the others have no stop). Decay is the paper
        result minus the historical one: expect it to be negative. Status changes only at the pre-registered looks;
        nothing is ever switched on automatically.
      </p>
    </>
  );
}
