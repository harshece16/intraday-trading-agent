import { useLocation, useNavigate } from "react-router-dom";
import { useApi } from "../api";
import LoadState from "../components/LoadState";
import { money, num, tone } from "../format";
import { nextSort, readSort, sortRows, writeSort } from "../sortRows";

// The single-rule paper lab (README sections 124 and 126): small rules, each with its
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

// Every column is sortable (README section 129). `get` is the value sorted on;
// a null reads as "—" and sorts last. One sort state serves all three cohort
// tables, so the cohorts stay separate sections and sort the same way inside.
// Text order for the status column: the ladder's rungs, not the alphabet.
const STATUS_ORDER = { collecting: "0 collecting", screen_failed: "1 screen failed", candidate: "2 candidate",
  confirmation_failed: "3 confirmation failed", confirmed: "4 confirmed" };
const COLUMNS = [
  { key: "rule", label: "Rule", kind: "text", get: (r) => r.rule },
  { key: "side", label: "Side", kind: "text", get: (r) => r.side },
  { key: "n", label: "Trades", kind: "num", get: (r) => r.n },
  { key: "win_rate", label: "Win rate", kind: "num", get: (r) => r.win_rate },
  { key: "break_even", label: "Break-even", kind: "num", get: (r) => r.break_even_win_rate },
  { key: "mean", label: "Net bp a trade", kind: "num", get: (r) => r.mean },
  { key: "ci", label: "95% interval", kind: "num", get: (r) => (r.ci ? r.ci[0] : null) },
  { key: "t", label: "t", kind: "num", get: (r) => r.t },
  { key: "net_r", label: "Net R", kind: "num", get: (r) => (r.r_based ? r.expectancy_r : null) },
  { key: "losing_run", label: "Losing run", kind: "num", get: (r) => (r.n ? r.max_consecutive_losses : null) },
  { key: "rupees_total", label: "Net ₹ (paper)", kind: "num", get: (r) => (r.n ? r.rupees_total : null) },
  { key: "rupees_today", label: "Today ₹ (paper)", kind: "num", get: (r) => (r.rupees_today ? r.rupees_today : null) },
  { key: "historical", label: "Historical bp", kind: "num", get: (r) => (r.historical ? r.historical.mean : null) },
  { key: "decay", label: "Decay", kind: "num", get: (r) => r.decay_bp },
  { key: "status", label: "Status", kind: "text", get: (r) => STATUS_ORDER[r.status] ?? "0 collecting" },
];
const NUM_COLS = new Set(["n", "win_rate", "break_even", "mean", "t", "net_r", "losing_run", "rupees_total", "rupees_today", "historical", "decay"]);

function useSort() {
  const location = useLocation();
  const navigate = useNavigate();
  const sort = readSort(location.search, COLUMNS);
  const onSort = (column) => {
    navigate({ pathname: location.pathname, search: writeSort(location.search, nextSort(sort, column)) }, { replace: true });
  };
  return [sort, onSort];
}

function SortHeader({ column, sort, onSort }) {
  const active = sort && sort.key === column.key;
  const dir = active ? sort.dir : null;
  const next = nextSort(sort, column);
  const hint = next ? `Sort by ${column.label}, ${next.dir === "asc" ? "low to high" : "high to low"}` : `Clear the sort on ${column.label}`;
  return (
    <th className={`sortable${NUM_COLS.has(column.key) ? " num" : ""}${active ? " sorted" : ""}`}
      aria-sort={dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"}>
      <button type="button" className="sorthead" onClick={() => onSort(column)} title={hint} aria-label={hint}>
        {column.label}<span className="sortmark" aria-hidden="true">{dir === "asc" ? "▲" : dir === "desc" ? "▼" : "↕"}</span>
      </button>
    </th>
  );
}

function Rupees({ v }) {
  if (v === null || v === undefined) return <span className="muted">—</span>;
  return <span className={tone(v)}>{money(v)}</span>;
}

function RuleTable({ rows, sort, onSort, cohort }) {
  const sorted = sortRows(rows, sort ? COLUMNS.find((c) => c.key === sort.key) : null, sort && sort.dir);
  const traded = rows.filter((r) => r.n > 0);
  const total = traded.reduce((a, r) => a + (r.rupees_total || 0), 0);
  const today = rows.reduce((a, r) => a + (r.rupees_today || 0), 0);
  return (
    <div className="table-wrap">
      <table className="datatable lab-table">
        <thead>
          <tr>{COLUMNS.map((c) => <SortHeader key={c.key} column={c} sort={sort} onSort={onSort} />)}</tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.rule}>
              <td className="lab-rule"><strong>{r.rule}</strong> {r.name}</td>
              <td className={r.side === "LONG" ? "up" : "down"}>{r.side === "LONG" ? "Long" : "Short"}</td>
              <td className="num">{r.n}{r.open ? <span className="muted"> +{r.open} open</span> : ""}</td>
              <td className="num">{rate(r.win_rate)}</td>
              <td className="num muted">{rate(r.break_even_win_rate)}</td>
              <td className={`num ${tone(r.mean)}`}>{bp(r.mean)}</td>
              <td className="muted">{interval(r.ci)}</td>
              <td className="num">{r.t != null ? r.t.toFixed(2) : "—"}</td>
              <td className={`num ${tone(r.expectancy_r)}`}>{r.r_based ? (r.expectancy_r != null ? `${r.expectancy_r >= 0 ? "+" : "−"}${Math.abs(r.expectancy_r).toFixed(2)}R` : "—") : ""}</td>
              <td className="num">{r.n ? r.max_consecutive_losses : "—"}</td>
              <td className="num"><Rupees v={r.n ? r.rupees_total : null} /></td>
              <td className="num"><Rupees v={r.rupees_today ? r.rupees_today : null} /></td>
              <td className={`num ${tone(r.historical && r.historical.mean)}`}>{r.historical ? bp(r.historical.mean) : "—"}</td>
              <td className={`num ${tone(r.decay_bp)}`}>{r.decay_bp != null ? bp(r.decay_bp) : "—"}</td>
              <td><StatusCell row={r} /></td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="lab-total">
            <td colSpan={10}>Cohort {cohort} total, paper: {traded.length} of {rows.length} rules have traded</td>
            <td className="num"><Rupees v={traded.length ? total : null} /></td>
            <td className="num"><Rupees v={today ? today : null} /></td>
            <td colSpan={3} className="muted">net of charges and slippage; no real money</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export default function RuleLab() {
  const { data, error, reload } = useApi("/api/rule-lab", 60000);
  const [sort, onSort] = useSort();
  if (!data) return <LoadState error={error} onRetry={reload} />;
  const rows = data.rules || [];
  const cohort1 = rows.filter((r) => r.cohort === 1);
  const cohort2 = rows.filter((r) => r.cohort === 2);
  const cohort4 = rows.filter((r) => r.cohort === 4);
  const alpha = (c) => (data.cohort_alpha && data.cohort_alpha[String(c)] != null ? `${(data.cohort_alpha[String(c)] * 100).toFixed(4).replace(/0+$/, "").replace(/\.$/, "")}%` : "—");
  const start4 = data.cohort_start && data.cohort_start["4"];
  const screenLeft = Math.max(0, data.screen_at - data.sessions);
  const anyTrades = rows.some((r) => r.n > 0 || r.open > 0);

  return (
    <>
      <h2 className="h">Rule lab <span className="pill neutral" style={{ verticalAlign: "middle" }}>Paper only</span></h2>
      <p className="sub">
        Each of {rows.length} small rules runs its own paper book on the day's list: {cohort1.length} of the lab's own
        (a candlestick pattern, a volume spike on an up or down bar, a trend turn, an opening-range break, a gap, a
        pullback to the 20-bar average), {cohort2.length} taken from popular YouTube trading videos and named
        traders' published rules (5-EMA, VWAP bounce, CPR and pivots, Supertrend, MACD, Stoch RSI, squeeze and more),
        and {cohort4.length} basic rules from the textbook (cohort 2b: the rest of the candlestick patterns, ADX,
        Fibonacci retracement, Ichimoku, Keltner, parabolic SAR, Donchian, VWAP bands, OBV, double tops and flags).
        On every finished 5-minute bar a rule that fires buys or shorts ₹{num(data.notional, 0)} at the next bar's
        open and closes {data.hold_minutes} minutes later, or by the 15:05 bar; the pullback and flag rules use a stop
        beyond the signal bar and a 3R target instead. No stops otherwise. Every trade pays about{" "}
        {num(data.round_trip_bp, 1)} bp of Zerodha charges and slippage. <strong>No orders are placed</strong>, and
        nothing here changes the engine's trades, risk or review queue.
      </p>
      <p className="muted">
        The rules and the test were fixed in advance (<code>{data.prereg}</code>). Nothing is judged before the
        look: after {data.screen_at} lab sessions, every rule is tested once, with a correction for testing
        {" "}{rows.length} rules at once (the lab's own rules at a {alpha(1)} error rate, the catalog rules at {alpha(2)}, cohort 2b at {alpha(4)}); a rule that passes becomes a candidate and must pass again on the next{" "}
        {data.confirm_sessions} sessions. Only then can it be proposed to you, and going live needs your yes and the
        engine's own live gate. <strong>Earlier tests of rules like these lost money after costs</strong> (the
        combination search, trials 128–202; the confluence engine, trial 40).
      </p>

      <div className="lab-money" aria-label="Paper rupees of the whole lab">
        <div><small>Net ₹ since the first session, paper</small><strong className={tone(data.rupees_total)}>{anyTrades ? money(data.rupees_total) : "—"}</strong>
          <small>on ₹{num(data.notional, 0)} a trade, summed over every closed trade; no real money</small></div>
        <div><small>Today ₹, paper{data.rupees_day ? ` (${data.rupees_day})` : ""}</small><strong className={tone(data.rupees_today)}>{data.rupees_today ? money(data.rupees_today) : "—"}</strong>
          <small>trades closed today, after charges and slippage</small></div>
      </div>

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
        Click a column heading to sort by it (again to flip, a third time to clear); the sort is kept in the page
        address and applies inside each cohort. Net ₹ is paper money on the lab&apos;s ₹{num(data.notional, 0)} a trade.
      </p>
      <p className="muted" style={{ fontSize: 12 }}>
        <strong>A short record says little.</strong> With a few dozen trades, a rule's average can be +20 bp or −20 bp
        by luck alone; the interval shows how wide that is. The running figures below are not a test.
      </p>

      {!anyTrades && <p className="empty">No paper trade yet. The lab starts with the first session after it is deployed.</p>}
      <h3 style={{ marginTop: 20 }}>The lab's own rules</h3>
      <LookNote rows={rows} which="screen" cohort={1} />
      <LookNote rows={rows} which="confirmation" cohort={1} />
      <RuleTable rows={cohort1} sort={sort} onSort={onSort} cohort={"1"} />
      <h3 style={{ marginTop: 24 }}>Rules from the strategy catalogs (YouTube and named traders)</h3>
      <p className="muted" style={{ fontSize: 12 }}>
        Each traded with the lab's exits (30 minutes, or a stop beyond the signal bar and a 3R target), not the
        video's own. Rules this project had already tested and found losing were left out.
      </p>
      <LookNote rows={rows} which="screen" cohort={2} />
      <LookNote rows={rows} which="confirmation" cohort={2} />
      <RuleTable rows={cohort2} sort={sort} onSort={onSort} cohort={"2"} />
      <h3 style={{ marginTop: 24 }}>Cohort 2b: the basic pattern and indicator rules (amendment 7)</h3>
      <p className="muted" style={{ fontSize: 12 }}>
        The 16 candlestick patterns of the engine's detector that cohort 1 did not trade, Doji and inside-bar
        breakouts, ADX, Fibonacci retracement, Ichimoku, Keltner, parabolic SAR, Donchian, VWAP bands and cross, OBV
        divergence, two time-of-day filters, double top/bottom and flags. Tested at {alpha(4)} (the budget's fourth
        slice; the third is reserved for daily rules) on its own first {data.screen_at} sessions
        {start4 ? `, from ${start4}` : " once it has its first trade"}. Candlestick patterns as a family already lost
        about 16.4 bp a trade after costs (trials 128–202), so expect the same here.
      </p>
      <LookNote rows={rows} which="screen" cohort={4} />
      <LookNote rows={rows} which="confirmation" cohort={4} />
      <RuleTable rows={cohort4} sort={sort} onSort={onSort} cohort={"2b"} />
      <p className="muted" style={{ fontSize: 12 }}>
        Net bp is after charges and slippage. Break-even is the win rate this rule's average win and loss would need
        to make nothing. Net R is for the pullback and flag rules only (the others have no stop). Decay is the paper
        result minus the historical one: expect it to be negative. Status changes only at the pre-registered looks;
        nothing is ever switched on automatically.
      </p>
    </>
  );
}
