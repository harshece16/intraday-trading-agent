import { useState } from "react";
import { useApi } from "../api";
import LoadState from "../components/LoadState";
import SymLink from "../components/SymLink";
import { num } from "../format";

const HORIZONS = [["f15", "15 min"], ["f30", "30 min"], ["f60", "60 min"]];
const TWO_LEG_BP = 33.26;

// The gate's checks (research/kronos_feature_ic.gate), in plain words.
const CHECKS = {
  spread_gt_two_leg: "the spread is above the two-leg bar",
  spread_t_gt_2: "t is above 2",
  sessions_ge_min: "there are at least 60 sessions",
  both_halves_positive: "both halves are positive",
  bh_survives: "it survives Benjamini–Hochberg at q = 0.10",
  partial_ic_t_gt_2: "the partial IC given m60 is positive with t above 2",
};

function bp(x, d = 1) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : "−"}${Math.abs(Number(x)).toFixed(d)} bp`;
}

function ic(x) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : "−"}${Math.abs(Number(x)).toFixed(3)}`;
}

function withT(value, s) {
  if (!s || s.mean === null || s.mean === undefined) return "—";
  const t = s.t === null || s.t === undefined ? "" : ` (t ${s.t < 0 ? "−" : ""}${Math.abs(Number(s.t)).toFixed(1)})`;
  return `${value}${t}`;
}

function toneOf(x) {
  return x > 0 ? "up" : x < 0 ? "down" : "";
}

function clock(iso) {
  return iso ? String(iso).slice(11, 16) : "";
}

function StageZeroTable({ records }) {
  if (!records || !records.length) return <p className="empty">No stage 0 record yet.</p>;
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead>
          <tr>
            <th>Record</th><th>Machine</th><th>Regression</th><th>Revisions</th><th>Lookahead</th>
            <th>Seconds per forecast</th><th>Sample count</th><th>Sessions</th><th>Stock-times</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.name}>
              <td>
                {r.name === "l40_stage0_pc" ? "PC" : r.name === "l40_stage0" ? "Mac" : r.name}
                <div className="muted" style={{ fontSize: 12 }}>{r.started ? String(r.started).slice(0, 16).replace("T", " ") : "—"}</div>
              </td>
              <td>{[r.machine, r.device, r.threads ? `${r.threads} threads` : null, r.torch ? `torch ${r.torch}` : null].filter(Boolean).join(", ") || "—"}</td>
              <td className={r.regression === "PASS" ? "up" : r.regression ? "down" : ""}>
                {r.regression || "—"}{r.regression_seconds ? <span className="muted"> in {r.regression_seconds} s</span> : null}
              </td>
              <td>
                {r.revisions && r.revisions.length
                  ? r.revisions.map((v) => <div key={v.repo}>{v.repo.replace("NeoQuasar/", "")} <code>{v.commit}</code> <span className="muted">{v.date}</span></div>)
                  : "—"}
              </td>
              <td className={r.lookahead_n && r.lookahead_identical === r.lookahead_n ? "up" : r.lookahead_n ? "down" : ""}>
                {r.lookahead_n ? `${r.lookahead_identical} of ${r.lookahead_n} identical` : "—"}
              </td>
              <td>{r.seconds_per_forecast != null ? num(r.seconds_per_forecast, 2) : "—"}
                {r.est_hours_at_sample_count_3 != null ? <div className="muted" style={{ fontSize: 12 }}>{num(r.est_hours_at_sample_count_3, 0)} h at sample count 3</div> : null}</td>
              <td>{r.sample_count_chosen ?? "—"}</td>
              <td>{r.sessions ?? "—"}{r.first_half != null ? <div className="muted" style={{ fontSize: 12 }}>{r.first_half} + {r.second_half}</div> : null}</td>
              <td>{r.stock_times != null ? num(r.stock_times, 0) : "—"}{r.dropped_count ? <div className="muted" style={{ fontSize: 12 }}>{r.dropped_count} dropped</div> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function verdict(h) {
  if (h.passes === true) return ["long", "Clears the gate"];
  if (h.passes === false) {
    const failed = Object.entries(h.checks || {}).filter(([, ok]) => !ok).map(([k]) => CHECKS[k] || k);
    return ["short", failed.length ? `Does not clear the gate: not that ${failed.join(", nor that ")}` : "Does not clear the gate"];
  }
  return ["neutral", "No verdict recorded"];
}

function ResultTable({ result }) {
  if (!result || !result.horizons || !Object.keys(result.horizons).length) {
    return <p className="empty">The measurement pass has not finished.</p>;
  }
  const bar = result.constants?.two_leg_bp ?? TWO_LEG_BP;
  return (
    <>
      <p className="muted" style={{ marginTop: 8 }}>
        Result recorded {result.finished ? String(result.finished).slice(0, 16).replace("T", " ") : "—"} ({result.status || "status unknown"}).
        The bar is a quintile spread above {num(bar, 2)} bp, two legs at the {num(result.constants?.round_trip_bp ?? bar / 2, 2)} bp round trip,
        with t above 2, positive in both halves, and a partial IC given the last hour's move that is also positive with t above 2.
      </p>
      <div className="table-wrap">
        <table className="datatable">
          <thead>
            <tr>
              <th>Horizon</th><th>Sessions</th><th>IC (t)</th><th>Partial IC given m60 (t)</th>
              <th>Quintile spread (t)</th><th>Halves</th><th>Top / bottom quintile</th><th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {HORIZONS.map(([key, label]) => {
              const h = result.horizons[key];
              if (!h) return <tr key={key}><td>{label}</td><td colSpan={7} className="muted">Not in the result</td></tr>;
              const [cls, words] = verdict(h);
              return (
                <tr key={key}>
                  <td>{label}</td>
                  <td>{h.sessions ?? "—"}</td>
                  <td className={toneOf(h.ic?.mean)}>{withT(ic(h.ic?.mean), h.ic)}</td>
                  <td className={toneOf(h.pic?.mean)}>{withT(ic(h.pic?.mean), h.pic)}</td>
                  <td className={h.spread?.mean > bar ? "up" : ""}>{withT(bp(h.spread?.mean), h.spread)}</td>
                  <td>{h.spread?.halves?.length ? h.spread.halves.map((m) => bp(m)).join(" / ") : "—"}</td>
                  <td>{bp(h.top?.mean)} / {bp(h.bottom?.mean)}</td>
                  <td><span className={`pill ${cls}`}>{h.passes === true ? "pass" : h.passes === false ? "fail" : "no verdict"}</span>
                    <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{words}</div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

function RunningStats({ stats, label }) {
  const rows = HORIZONS.filter(([key]) => stats && stats[key]);
  if (!rows.length) {
    return <p className="empty">No running statistics yet: they start once ten stocks at a time have a realised target.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead>
          <tr><th>Horizon</th><th>{label}</th><th>IC (t)</th><th>Partial IC given m60 (t)</th><th>Quintile spread (t)</th><th>Top / bottom quintile</th></tr>
        </thead>
        <tbody>
          {rows.map(([key, name]) => {
            const s = stats[key];
            return (
              <tr key={key}>
                <td>{name}</td>
                <td>{s.times ?? s.sessions ?? "—"}</td>
                <td className={toneOf(s.ic?.mean)}>{withT(ic(s.ic?.mean), s.ic)}</td>
                <td className={toneOf(s.pic?.mean)}>{withT(ic(s.pic?.mean), s.pic)}</td>
                <td className={toneOf(s.spread?.mean)}>{withT(bp(s.spread?.mean), s.spread)}</td>
                <td>{bp(s.top?.mean)} / {bp(s.bottom?.mean)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ShadowDay({ day }) {
  const [hhmm, setHhmm] = useState(null);
  if (!day) {
    return (
      <p className="empty">
        No shadow day yet. The shadow writes <code>backend/data/kronos_shadow_&lt;date&gt;.json</code> every five minutes of a
        session while it runs; the page picks it up on its next refresh.
      </p>
    );
  }
  const times = day.hhmm_list || [];
  const shown = hhmm && times.includes(hhmm) ? hhmm : day.latest_hhmm;
  const rows = (day.forecasts || []).filter((r) => r.hhmm === shown)
    .sort((a, b) => (b.f60 ?? -Infinity) - (a.f60 ?? -Infinity));
  const stats = day.summary?.stats && Object.keys(day.summary.stats).length ? day.summary.stats : day.running;
  return (
    <>
      <p className="muted" style={{ marginTop: -4 }}>
        {day.date}: {day.rows ?? 0} forecasts on {day.stocks ?? 0} stocks at {day.times ?? 0} times
        {day.bars_delayed ? `, ${day.bars_delayed} on delayed bars` : ", all on live bars"}
        {day.sample_count ? `, sample count ${day.sample_count}` : ""}{day.device ? ` on ${day.device}` : ""}.
        {day.realised ? ` ${day.realised} have a realised target.` : " No target is realised yet."}
        {day.updated ? ` Updated ${clock(day.updated)}.` : ""}
      </p>
      {times.length > 1 && (
        <div className="sortbar" role="tablist" aria-label="Forecast time">
          <span>Time</span>
          {times.map((t) => (
            <button key={t} className={`sortbtn ${t === shown ? "active" : ""}`} role="tab" aria-selected={t === shown} onClick={() => setHhmm(t)}>{t}</button>
          ))}
        </div>
      )}
      {rows.length ? (
        <div className="table-wrap">
          <table className="datatable">
            <thead>
              <tr>
                <th>Stock</th><th title="The stronger side of the old selection score. Since README section 115 it is information only: the engine no longer acts on it">Score's side</th><th>Scanner score</th><th>Forecast 15 min</th><th>Forecast 30 min</th><th>Forecast 60 min</th>
                <th>Bars</th><th>Realised 15 / 30 / 60</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.hhmm}-${r.symbol}`}>
                  <td><SymLink sym={r.symbol} /></td>
                  <td>{r.scanner?.side ? <span className={`pill ${r.scanner.side === "SHORT" ? "short" : "long"}`}>{r.scanner.side === "SHORT" ? "Short" : "Long"}</span> : <span className="muted">—</span>}</td>
                  <td>{r.scanner?.score != null ? num(r.scanner.score, 1) : "—"}</td>
                  <td className={toneOf(r.f15)}>{bp(r.f15)}</td>
                  <td className={toneOf(r.f30)}>{bp(r.f30)}</td>
                  <td className={toneOf(r.f60)}>{bp(r.f60)}</td>
                  <td className={r.bars_delayed ? "muted" : ""}>{r.bars_delayed === null || r.bars_delayed === undefined ? "—" : r.bars_delayed ? "delayed" : "live"}</td>
                  <td>{r.targets ? [r.targets.f15, r.targets.f30, r.targets.f60].map((v) => bp(v)).join(" / ") : <span className="muted">not yet</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="empty">No forecasts at {shown || "this time"}.</p>}

      <h4 style={{ marginTop: 20 }}>Running statistics{day.summary ? " (the day's summary)" : ""}</h4>
      <RunningStats stats={stats} label="Times" />
      <p className="muted" style={{ fontSize: 12 }}>
        Across the stocks at one time, then averaged across times. One day is an anecdote, not a test: the test is the
        79-session pass above, and no threshold applies to a shadow day.
      </p>
    </>
  );
}

function DaysTable({ days, selected, onSelect }) {
  if (!days || !days.length) return <p className="empty">No shadow days yet.</p>;
  return (
    <div className="table-wrap">
      <table className="datatable">
        <thead>
          <tr><th>Date</th><th>Forecasts</th><th>Stocks</th><th>Times</th><th>Bars live / delayed</th>
            <th>IC 15 min (t)</th><th>IC 30 min (t)</th><th>IC 60 min (t)</th></tr>
        </thead>
        <tbody>
          {days.map((d) => (
            <tr key={d.date} className={d.date === selected ? "active" : ""}>
              <td><button className="more" onClick={() => onSelect(d.date)}>{d.date}</button></td>
              <td>{d.rows ?? "—"}</td><td>{d.stocks ?? "—"}</td><td>{d.times ?? "—"}</td>
              <td>{d.bars_live ?? "—"} / {d.bars_delayed ?? "—"}</td>
              {HORIZONS.map(([key]) => (
                <td key={key} className={toneOf(d.ic?.[key]?.mean)}>{withT(ic(d.ic?.[key]?.mean), d.ic?.[key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Kronos() {
  const { data, error, reload } = useApi("/api/kronos", 60000);
  const [pickedDate, setPickedDate] = useState(null);
  const picked = useApi(pickedDate && pickedDate !== data?.today?.date ? `/api/kronos/day/${pickedDate}` : null, 60000);
  if (!data) return <LoadState error={error} onRetry={reload} />;

  const look = data.look || {};
  const showingToday = !pickedDate || pickedDate === data.today?.date;
  const day = showingToday ? data.today : picked.data;
  // The backend sends today's day when there is one, else the latest; say which.
  const todayHeading = data.today && data.today.date !== data.date_today ? "Latest shadow day" : "Today's shadow";
  // Once the look's one pass has failed at every horizon, the shadow is a record of a failed model, and says so.
  const horizons = look.result?.status === "DONE" ? Object.values(look.result.horizons || {}) : [];
  const failedTest = horizons.length > 0 && horizons.every((h) => h.passes === false);
  const spreads = horizons.map((h) => h.spread?.mean).filter((v) => typeof v === "number");
  const bestGap = { bp: spreads.length ? Math.max(...spreads).toFixed(1) : "?", sessions: horizons[0]?.sessions ?? "?" };
  const twoLeg = look.result?.constants?.two_leg_bp ?? 33.26;

  return (
    <>
      <h2 className="h">Kronos <span className="pill neutral" style={{ verticalAlign: "middle" }}>Research look L40</span></h2>
      <p className="sub">
        Kronos is an open-source price-forecasting model: a transformer trained on candlestick bars that, given the last
        few hours of five-minute bars, writes the next hour of bars. The project tests it as research look L40, pre-registered
        before any forecast was computed: does the forecast rank the next 15, 30 or 60 minutes across the day's stocks,
        beyond what the last hour's move already says? <strong>Nothing here affects a trade.</strong> No entry, no size, no
        exit and no scanner score reads this page or its database; it is a place to see the data.
      </p>
      <p className="muted" style={{ marginTop: -8 }}>
        1 basis point = 0.01% of the price; 100 bp = 1%. Forecasts and realised moves are in basis points of the last close.
        IC is the rank correlation between forecast and outcome across stocks: +1 is perfect order, 0 is none.
      </p>

      <h3 style={{ marginTop: 24 }}>The test</h3>
      <p className="muted" style={{ marginTop: -4 }}>
        Stage 0 is the set of checks made before any forecast met a return: the authors' own regression test, the pinned model
        revisions, a lookahead proof on 20 stock-times, the timing that fixed the sample count, and the sample's coverage.
      </p>
      <StageZeroTable records={look.stage0} />
      <h4 style={{ marginTop: 16 }}>Result</h4>
      <ResultTable result={look.result} />

      <h3 style={{ marginTop: 24 }}>{showingToday ? todayHeading : `Shadow day ${pickedDate}`}
        {failedTest && <span className="pill short" style={{ marginLeft: 10, verticalAlign: "middle" }}>Kronos shadow: failed test L40 (record only, not a signal)</span>}
        {!showingToday && <button className="more" style={{ marginLeft: 10 }} onClick={() => setPickedDate(null)}>Back to the latest day</button>}
      </h3>
      {failedTest && (
        <p className="muted" style={{ marginTop: -4 }}>
          Zero-shot Kronos failed its pre-registered test on {bestGap.sessions} past sessions at 15, 30 and 60 minutes (best
          top-minus-bottom gap {bestGap.bp} bp before costs, {twoLeg} bp needed). Its live forecasts are recorded for comparison;
          nothing reads them to trade.
        </p>
      )}
      {!showingToday && !picked.data ? <LoadState error={picked.error} onRetry={picked.reload} /> : <ShadowDay day={day} />}

      <h3 style={{ marginTop: 24 }}>Days</h3>
      <DaysTable days={data.days} selected={day?.date} onSelect={setPickedDate} />

      <p className="muted" style={{ fontSize: 12, marginTop: 20 }}>
        Source: the shadow's files in backend/data and the look's records in docs/research/data, read into backend/data/kronos.db
        on each load of this page. Pre-registration: {data.prereg || "docs/research/prereg-kronos-feature-ic.md"}. A day's forecasts
        and their outcomes are recorded, not concluded from; no result on this page is a reason to trade.
      </p>
    </>
  );
}
