import { useApi } from "../api";
import LoadState from "../components/LoadState";
import { num } from "../format";
import SymLink from "../components/SymLink";

const SIZE = ["none", "half", "normal", "double"];

function bp(x, d = 1) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : "−"}${Math.abs(Number(x)).toFixed(d)} bp`;
}

function clock(iso) {
  return iso ? String(iso).slice(11, 16) : "";
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

// While today's round is open: what is held, when it closes, and where it stands at
// Kite's prices. The mark is for watching only. The backend never stores or scores it.
function OpenRound({ live }) {
  const held = live.positions;
  const title = held
    ? `${plural(held, "paper position")} ${held === 1 ? "is" : "are"} open`
    : "Today's round is open, with no position";
  return (
    <div className="plan">
      <h3>{title}</h3>
      <p>
        {live.opened_at ? `Opened at ${clock(live.opened_at)}. ` : ""}
        {held ? `They close at the ${live.closes_at} square-off, and only that close is scored.` : "Jev skipped every stock."}
        {live.excluded ? ` ${plural(live.excluded, "decision")} had no live entry price and ${live.excluded === 1 ? "is" : "are"} left out.` : ""}
      </p>
      {held > 0 && (live.mean_net_bp !== null && live.mean_net_bp !== undefined ? (
        <p>
          If closed now: Jev <strong className={toneOf(live.mean_net_bp)}>{bp(live.mean_net_bp)}</strong> a position
          after costs, the scanner alone <strong className={toneOf(live.scanner_mean_net_bp)}>{bp(live.scanner_mean_net_bp)}</strong>.
          Marked at {clock(live.marked_at)} from Kite
          {live.priced < held ? `, ${live.priced} of ${held} priced` : ""}. This is a live mark, not a result.
        </p>
      ) : (
        <p>No live mark: {live.reason || "Kite gave no price"}. The positions stay open.</p>
      ))}
    </div>
  );
}

function toneOf(x) {
  return x > 0 ? "up" : x < 0 ? "down" : "";
}

// A round that stopped part-way (#158): the decisions made before the stop are
// still closed and scored at 15:08; the stocks after it were never asked.
function Interrupted({ intr }) {
  const why = intr.reason === "no_live_prices" ? "Kite stopped giving live prices" : "Jev couldn't be reached";
  const rest = intr.not_asked || [];
  return (
    <p className="muted">
      Today's round stopped after {intr.asked} of {intr.asked + rest.length} stocks at {(intr.at || "").slice(11, 16)}:
      {" "}{why} (<code>{intr.error}</code>). The {intr.asked} decisions it made are scored at the 15:08 close like
      any other round{rest.length ? `; ${rest.join(", ")} ${rest.length === 1 ? "was" : "were"} not asked` : ""}.
    </p>
  );
}

export default function JevBook() {
  const { data, error, reload } = useApi("/api/jev-book", 30000);
  if (!data) return <LoadState error={error} onRetry={reload} />;

  const day = data.last_day;
  const unavailable = day && day.status === "jev_unavailable";
  const noLive = day && day.status === "no_live_prices";
  const live = data.live;                     // present only while today's round is open
  const marks = (live && live.marks) || {};
  const statusPill = data.status === "switched_off" ? ["short", "Switched off"]
    : unavailable ? ["wait", "Jev unavailable"] : noLive ? ["wait", "No live prices"]
      : live ? ["long", `Open until ${live.closes_at}`] : ["neutral", "Paper test"];

  return (
    <>
      <h2 className="h">Jev book <span className={`pill ${statusPill[0]}`} style={{ verticalAlign: "middle" }}>{statusPill[1]}</span></h2>
      <p className="sub">
        Every trading day at 09:45, Jev (an LLM judge) is shown each stock on the scanner's shortlist and asked:
        buy, short or skip; how likely it is to close higher; and how large a position. Each buy or short is a
        paper position closed at the 15:08 square-off, after about {num(data.round_trip_bp, 1)} bp of costs, and
        compared with the side the scanner's old score favours on the same stock, the baseline this test was registered
        with (the engine itself no longer acts on that side). <strong>Paper only.</strong> The
        research found no LLM trader with an edge after costs; this test checks, rather than assumes.
      </p>
      {data.status_reason && <p className="muted">{data.status_reason}</p>}
      {!data.key_stored && !unavailable && !live && (
        <p className="muted">No TypeSafe API key is stored yet, so no round will run. Create one at console.typesafe.ai/keys
          and store it with <code>pbpaste | backend/.venv/bin/python backend/typesafe_key.py set</code>.</p>
      )}
      {noLive && (
        <p className="muted">
          Kite had no live session when today's round was due (not connected, or not reconnected since Zerodha's
          06:00 cutoff), so Jev wasn't asked and the day doesn't count toward the test: its fills must be live
          prices, not the delayed fallback. Reconnect Kite on the dashboard before 09:15 on trading days.
        </p>
      )}
      {day && day.interrupted && <Interrupted intr={day.interrupted} />}
      {unavailable && (
        <p className="muted">
          Today Jev couldn't be reached: <code>{day.error}</code>. Create a key at console.typesafe.ai/keys, copy it,
          and store it with <code>pbpaste | backend/.venv/bin/python backend/typesafe_key.py set</code>; the next
          trading day's round runs automatically.
        </p>
      )}

      {live && <OpenRound live={live} />}

      <div className="grid3" style={{ margin: "16px 0" }}>
        <div className="stat"><small>Jev, net per closed trade</small>
          <strong className={toneOf(data.mean_net_bp)}>{bp(data.mean_net_bp)}</strong>
          <small>{data.traded} closed{live && live.positions ? ` · ${live.positions} open now` : ""} · t {data.t != null ? data.t.toFixed(2) : "—"} · hit rate {data.hit_rate != null ? `${(data.hit_rate * 100).toFixed(0)}%` : "—"}</small></div>
        <div className="stat"><small>Scanner alone, same stocks</small>
          <strong className={toneOf(data.scanner_mean_net_bp)}>{bp(data.scanner_mean_net_bp)}</strong>
          <small>Jev minus scanner {bp(data.paired_vs_scanner_bp)} · t {data.paired_t != null ? data.paired_t.toFixed(2) : "—"}</small></div>
        <div className="stat"><small>Sessions · decisions · skips</small>
          <strong>{data.sessions_closed} · {data.decisions} · {data.skips}</strong>
          <small>Probability score (Brier) {data.brier != null ? data.brier.toFixed(3) : "—"} — a coin scores 0.250</small></div>
      </div>
      <p className="muted" style={{ fontSize: 12 }}>
        Verdict after 300 buy/short trades or 60 sessions: Jev must be positive after costs with t ≥ 2.24, in both
        halves, and beat the scanner. It switches itself off if, after 100 trades, it is clearly losing (t below −2).
        {data.verdict_due ? " The verdict is now due." : ""}
      </p>

      <h3 style={{ marginTop: 24 }}>Latest session{day ? ` — ${day.date}` : ""}</h3>
      {day && day.decisions && day.decisions.length ? (
        <div className="table-wrap">
          <table className="datatable">
            <thead><tr><th>Stock</th><th>Jev</th><th>P(up)</th><th>Size</th><th>Scanner</th><th>Entry</th>
              {live
                ? <><th>Now</th><th>Move so far</th><th>Jev, if closed now</th><th>Scanner, if closed now</th></>
                : <><th>Exit</th><th>Move</th><th>Jev net</th><th>Scanner net</th></>}
            </tr></thead>
            <tbody>
              {day.decisions.map((d) => (
                <tr key={d.symbol}>
                  <td><SymLink sym={d.symbol} /></td>
                  <td className={d.action === "buy" ? "up" : d.action === "short" ? "down" : "muted"}>{d.action || "—"}</td>
                  <td>{d.p_up != null ? d.p_up.toFixed(2) : "—"}</td>
                  <td>{d.size_level != null ? SIZE[d.size_level] : "—"}</td>
                  <td>{d.scanner_side || "—"}</td>
                  <td>{d.entry != null ? num(d.entry) : <span className="muted">{d.excluded || "—"}</span>}</td>
                  {live ? (() => {
                    const m = marks[d.symbol];
                    if (!m) return <td colSpan={4} className="muted">{d.entry != null ? "No live price" : ""}</td>;
                    return <>
                      <td>{num(m.ltp)}</td>
                      <td className={toneOf(m.move_bp)}>{bp(m.move_bp, 0)}</td>
                      <td className={toneOf(m.net_bp)}>{d.action === "skip" ? "skipped" : bp(m.net_bp, 0)}</td>
                      <td className={toneOf(m.scanner_net_bp)}>{bp(m.scanner_net_bp, 0)}</td>
                    </>;
                  })() : <>
                    <td>{d.exit != null ? num(d.exit) : "—"}</td>
                    <td className={toneOf(d.move_bp)}>{bp(d.move_bp, 0)}</td>
                    <td className={toneOf(d.net_bp)}>{bp(d.net_bp, 0)}</td>
                    <td className={toneOf(d.scanner_net_bp)}>{bp(d.scanner_net_bp, 0)}</td>
                  </>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="empty">{day ? "No decisions that day." : "No session yet — the first round runs at 09:45 on the next trading day."}</p>}
    </>
  );
}
