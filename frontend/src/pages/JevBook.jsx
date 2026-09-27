import { useEffect, useState } from "react";
import { apiJson } from "../api";
import { num } from "../format";
import SymLink from "../components/SymLink";

const SIZE = ["none", "half", "normal", "double"];

function bp(x, d = 1) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : ""}${Number(x).toFixed(d)} bp`;
}

function toneOf(x) {
  return x > 0 ? "up" : x < 0 ? "down" : "";
}

export default function JevBook() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    const load = () => apiJson("/api/jev-book")
      .then((d) => { if (alive) { setData(d); setError(null); } })
      .catch((e) => { if (alive) setError(e.message); });
    load();
    const t = setInterval(load, 60000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  if (error) return <p className="empty">Couldn't load the Jev book: {error}</p>;
  if (!data) return <p className="empty">Loading…</p>;

  const day = data.last_day;
  const unavailable = day && day.status === "jev_unavailable";
  const statusPill = data.status === "switched_off" ? ["short", "Switched off"]
    : unavailable ? ["wait", "Jev unavailable"] : ["neutral", "Paper test"];

  return (
    <>
      <h2 className="h">Jev book <span className={`pill ${statusPill[0]}`} style={{ verticalAlign: "middle" }}>{statusPill[1]}</span></h2>
      <p className="sub">
        Every trading day at 09:45, Jev (an LLM judge) is shown each stock on the scanner's shortlist and asked:
        buy, short or skip; how likely it is to close higher; and how large a position. Each buy or short is a
        paper position closed at the 15:08 square-off, after about {num(data.round_trip_bp, 1)} bp of costs, and
        compared with what the scanner alone would have done on the same stock. <strong>Paper only.</strong> The
        research found no LLM trader with an edge after costs; this test checks, rather than assumes.
      </p>
      {data.status_reason && <p className="muted">{data.status_reason}</p>}
      {!data.key_stored && !unavailable && (
        <p className="muted">No TypeSafe API key is stored yet, so no round will run. Create one at console.typesafe.ai/keys
          and store it with <code>pbpaste | backend/.venv/bin/python backend/typesafe_key.py set</code>.</p>
      )}
      {unavailable && (
        <p className="muted">
          Today Jev couldn't be reached: <code>{day.error}</code>. Create a key at console.typesafe.ai/keys, copy it,
          and store it with <code>pbpaste | backend/.venv/bin/python backend/typesafe_key.py set</code>; the next
          trading day's round runs automatically.
        </p>
      )}

      <div className="grid3" style={{ margin: "16px 0" }}>
        <div className="stat"><small>Jev, net per trade</small>
          <strong className={toneOf(data.mean_net_bp)}>{bp(data.mean_net_bp)}</strong>
          <small>{data.traded} trades · t {data.t != null ? data.t.toFixed(2) : "—"} · hit rate {data.hit_rate != null ? `${(data.hit_rate * 100).toFixed(0)}%` : "—"}</small></div>
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
            <thead><tr><th>Stock</th><th>Jev</th><th>P(up)</th><th>Size</th><th>Scanner</th><th>Entry</th><th>Exit</th><th>Move</th><th>Jev net</th><th>Scanner net</th></tr></thead>
            <tbody>
              {day.decisions.map((d) => (
                <tr key={d.symbol}>
                  <td><SymLink sym={d.symbol} /></td>
                  <td className={d.action === "buy" ? "up" : d.action === "short" ? "down" : "muted"}>{d.action || "—"}</td>
                  <td>{d.p_up != null ? d.p_up.toFixed(2) : "—"}</td>
                  <td>{d.size_level != null ? SIZE[d.size_level] : "—"}</td>
                  <td>{d.scanner_side || "—"}</td>
                  <td>{d.entry != null ? num(d.entry) : "—"}</td><td>{d.exit != null ? num(d.exit) : "—"}</td>
                  <td className={toneOf(d.move_bp)}>{bp(d.move_bp, 0)}</td>
                  <td className={toneOf(d.net_bp)}>{bp(d.net_bp, 0)}</td>
                  <td className={toneOf(d.scanner_net_bp)}>{bp(d.scanner_net_bp, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="empty">{day ? "No decisions that day." : "No session yet — the first round runs at 09:45 on the next trading day."}</p>}
    </>
  );
}
