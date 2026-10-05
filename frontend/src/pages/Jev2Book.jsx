import { Link } from "react-router-dom";
import { useApi } from "../api";
import LoadState from "../components/LoadState";
import { num } from "../format";
import SymLink from "../components/SymLink";

const REPO = "https://github.com/harshece16/intraday-trading-agent/blob/main";

function bp(x, d = 1) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : "−"}${Math.abs(Number(x)).toFixed(d)} bp`;
}

function t2(x) {
  return x === null || x === undefined ? "—" : Number(x).toFixed(2);
}

function toneOf(x) {
  return x > 0 ? "up" : x < 0 ? "down" : "";
}

const QUESTION_LABEL = {
  news_positive: "news positive", news_negative: "news negative", strength_extending: "strength extending",
  weakness_extending: "weakness extending", sector_up: "sector up", sector_down: "sector down",
  move_exhausted: "move exhausted", p_combined: "combined",
};

// A round that stopped part-way: the decisions made before the stop are still
// closed and scored at 15:08; the stocks after it were never asked.
function Interrupted({ intr }) {
  const why = intr.reason === "no_live_prices" ? "Kite stopped giving live prices" : "Jev couldn't be reached";
  const rest = intr.not_asked || [];
  return (
    <p className="muted">
      Today's round stopped after {intr.asked} of {intr.asked + rest.length} stocks at {(intr.at || "").slice(11, 16)}:
      {" "}{why} (<code>{intr.error}</code>). The {intr.asked} decisions it made are scored at the 15:08 close
      {rest.length ? `; ${rest.join(", ")} ${rest.length === 1 ? "was" : "were"} not asked` : ""}.
    </p>
  );
}

export default function Jev2Book() {
  const { data, error, reload } = useApi("/api/jev2-book", 30000);
  if (!data) return <LoadState error={error} onRetry={reload} />;

  const day = data.last_day;
  const status = day && day.status;
  const isOpen = status === "open" || status === "deciding";
  const pill = data.status === "switched_off" ? ["short", "Switched off"]
    : status === "jev_unavailable" ? ["wait", "Jev unavailable"]
      : status === "no_live_prices" ? ["wait", "No live prices"]
        : status === "missed" ? ["wait", "Missed today"]
          : isOpen ? ["long", "Round open until 15:08"] : ["neutral", "Paper test"];
  const th = data.thresholds || {};
  const briers = data.briers || {};
  const band = data.jev1_by_band;

  return (
    <>
      <h2 className="h">Jev 2 book <span className={`pill ${pill[0]}`} style={{ verticalAlign: "middle" }}>{pill[1]}</span></h2>
      <p className="sub">
        A second paper test of the Jev judge, run beside the <Link to="/jev-book">Jev book</Link> and leaving it
        untouched. Each trading day, once Jev 1's 09:45 round has ended, Jev is shown a <strong>blind</strong> state
        for every one of the 25 names on the day's list: prices, gap, relative volume, VWAP distance, opening range,
        sector and NIFTY change, three dated headlines (title, publisher, age), the market summary and the cost line; never the scanner's
        side, score, reasons or chart labels. It answers <strong>seven narrow yes/no questions</strong>, each in two
        wordings, and a frozen rule combines them: buy if the combined probability is at or above {th.buy_at ?? 0.65},
        short at or below {th.short_at ?? 0.35}, otherwise skip; skip too when the move looks exhausted
        (≥ {th.exhausted_veto ?? 0.7}). A buy or short is a paper position closed at the 15:08 square-off after
        about {num(data.round_trip_bp, 1)} bp of costs; on the 15 names it shares with Jev 1 it fills at the same
        Kite price Jev 1 recorded. <strong>Paper only.</strong> Model <code>{data.model}</code>, pinned.{" "}
        <a href={`${REPO}/docs/research/prereg-jev2-book.md`} target="_blank" rel="noreferrer">Pre-registration</a>.
      </p>
      {data.status_reason && <p className="muted">{data.status_reason}</p>}
      {!data.key_stored && status !== "jev_unavailable" && (
        <p className="muted">No TypeSafe API key is stored yet, so no round will run. Store one with{" "}
          <code>pbpaste | backend/.venv/bin/python backend/typesafe_key.py set</code>.</p>
      )}
      {status === "no_live_prices" && (
        <p className="muted">Kite had no live session when the round was due, so Jev was not asked and the day
          does not count: fills must be live prices.</p>
      )}
      {status === "missed" && <p className="muted">The round did not start by 10:00: {day.error}. The day does not count.</p>}
      {status === "jev_unavailable" && <p className="muted">Today Jev couldn't be reached: <code>{day.error}</code>.</p>}
      {day && day.interrupted && <Interrupted intr={day.interrupted} />}

      <div className="grid3" style={{ margin: "16px 0" }}>
        <div className="stat"><small>Jev 2, net per closed trade</small>
          <strong className={toneOf(data.mean_net_bp)}>{bp(data.mean_net_bp)}</strong>
          <small>{data.traded} closed · clustered t {t2(data.t_clustered)} (plain {t2(data.t)}) · hit rate{" "}
            {data.hit_rate != null ? `${(data.hit_rate * 100).toFixed(0)}%` : "—"}</small></div>
        <div className="stat"><small>Scanner's side, every decision (skips at 0)</small>
          <strong className={toneOf(data.scanner_mean_net_bp)}>{bp(data.scanner_mean_net_bp)}</strong>
          <small>{data.scanner_n ?? 0} decisions · Jev 2 minus scanner {bp(data.paired_vs_scanner_bp)} · clustered t {t2(data.paired_t_clustered)}</small></div>
        <div className="stat"><small>Jev 2 minus Jev 1, shared names</small>
          <strong className={toneOf(data.paired_vs_jev1_bp)}>{bp(data.paired_vs_jev1_bp)}</strong>
          <small>{data.paired_vs_jev1_n} pairs · clustered t {t2(data.paired_vs_jev1_t_clustered)} · reported, not gated</small></div>
      </div>
      <div className="grid3" style={{ margin: "0 0 16px" }}>
        <div className="stat"><small>Sessions · decisions · skips</small>
          <strong>{data.sessions_closed} · {data.decisions} · {data.skips}</strong>
          <small>skip rate {data.skip_rate != null ? `${(data.skip_rate * 100).toFixed(0)}%` : "—"} · halves{" "}
            {bp(data.halves?.[0], 0)} / {bp(data.halves?.[1], 0)}</small></div>
        <div className="stat"><small>Shared 15 · extra 10</small>
          <strong>{bp(data.shared_mean_net_bp)} · {bp(data.extra_mean_net_bp)}</strong>
          <small>{data.shared_n} and {data.extra_n} closed trades</small></div>
        <div className="stat"><small>Brier, combined probability</small>
          <strong>{briers.p_combined != null ? briers.p_combined.toFixed(3) : "—"}</strong>
          <small>a coin scores 0.250 · {Object.keys(briers).filter((k) => k !== "p_combined" && briers[k] != null)
            .map((k) => `${QUESTION_LABEL[k] || k} ${briers[k].toFixed(2)}`).join(" · ") || "no closed decision yet"}</small></div>
      </div>
      <p className="muted" style={{ fontSize: 12 }}>
        Verdict once, after 300 buy/short trades or 60 sessions: positive after costs with a session-clustered
        t ≥ 2.39 (the "LLM judgment" family, now three tests), in both halves, and ahead of the scanner's side
        (paired clustered t ≥ 1.65). It switches itself off if, after 100 trades, it is clearly losing (t below −2).
        {data.verdict_due ? " The verdict is now due." : ""}
        {band && (band.inside.n || band.outside.n) ? ` Jev 1's record cut by |P(up) − 0.5|, information only: inside 0.15 ${band.inside.n} trades ${bp(band.inside.mean_bp)}, outside ${band.outside.n} trades ${bp(band.outside.mean_bp)}.` : ""}
      </p>

      <h3 style={{ marginTop: 24 }}>Latest session{day ? ` — ${day.date}` : ""}</h3>
      {day && day.decisions && day.decisions.length ? (
        <div className="table-wrap">
          <table className="datatable">
            <thead><tr><th>Stock</th><th>Jev 2</th><th>P(combined)</th><th>News +/−</th><th>Trend +/−</th><th>Sector +/−</th>
              <th>Exhausted</th><th>Scanner</th><th>Fill</th><th>Entry</th><th>Exit</th><th>Move</th><th>Jev 2 net</th><th>Scanner net</th>
            </tr></thead>
            <tbody>
              {day.decisions.map((d) => {
                const p = d.p || {};
                const pair = (a, b) => (p[a] != null && p[b] != null ? `${p[a].toFixed(2)} / ${p[b].toFixed(2)}` : "—");
                return (
                  <tr key={d.symbol}>
                    <td><SymLink sym={d.symbol} />{d.shared ? "" : <small className="muted"> extra</small>}</td>
                    <td className={d.action === "buy" ? "up" : d.action === "short" ? "down" : "muted"}>{d.action || "—"}</td>
                    <td>{d.p_combined != null ? d.p_combined.toFixed(2) : "—"}</td>
                    <td>{pair("news_positive", "news_negative")}</td>
                    <td>{pair("strength_extending", "weakness_extending")}</td>
                    <td>{pair("sector_up", "sector_down")}</td>
                    <td>{p.move_exhausted != null ? p.move_exhausted.toFixed(2) : "—"}</td>
                    <td>{d.scanner_side || "—"}</td>
                    <td className="muted">{d.fill_source === "jev1" ? "Jev 1's" : d.fill_source === "own" ? "own" : "—"}</td>
                    <td>{d.entry != null ? num(d.entry) : <span className="muted">{d.excluded || "—"}</span>}</td>
                    <td>{d.exit != null ? num(d.exit) : "—"}</td>
                    <td className={toneOf(d.move_bp)}>{bp(d.move_bp, 0)}</td>
                    <td className={toneOf(d.net_bp)}>{d.action === "skip" ? "skipped" : bp(d.net_bp, 0)}</td>
                    <td className={toneOf(d.scanner_net_bp)}>{bp(d.scanner_net_bp, 0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : <p className="empty">{day ? "No decisions that day." : "No session yet — the first round runs after Jev 1's on the next trading day."}</p>}
      <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
        Each probability is the mean of two wordings of the same question. "Fill: Jev 1's" means the entry and exit
        are the Kite prices Jev 1 recorded for the same stock-day, so the pair is exact; "own" means Jev 2 fetched
        its own. There is no live mark on this page: the record is the 15:08 close alone.
      </p>
    </>
  );
}
