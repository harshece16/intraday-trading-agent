import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "../api";
import { clock, num } from "../format";

const STANCE_CLASS = { bullish: "up", bearish: "down", support: "up", reject: "down" };
const RATING_CLASS = { 2: "up", 1: "up", 0: "", "-1": "down", "-2": "down" };
const STATUS_TEXT = { pending: "Waiting", running: "Working…", done: "Done", error: "Failed", skipped: "Skipped" };
const PROPOSAL_TEXT = { long: "Go long", short: "Go short", stand_aside: "Stand aside" };
const GRID = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12, marginTop: 8 };

async function call(path, body) {
  const res = await apiFetch(path, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

function Points({ items }) {
  if (!items || !items.length) return null;
  return (
    <ul className="evidence">
      {items.map((p, i) => (
        <li key={i}>
          <span></span>
          <span>{p.text} <span className="muted" style={{ fontSize: 12 }}>({(p.citations || []).join(", ")})</span></span>
        </li>
      ))}
    </ul>
  );
}

function Stance({ value }) {
  if (!value) return <span className="pill neutral">No report</span>;
  return <span className={`pill ${STANCE_CLASS[value] ? (STANCE_CLASS[value] === "up" ? "long" : "short") : "neutral"}`}>{value.replace("_", " ")}</span>;
}

function Progress({ run, symbol }) {
  if (!run || !run.running || run.current !== symbol || !run.stages?.length) return null;
  return (
    <div className="table-wrap" style={{ marginTop: 12 }}>
      <table className="datatable">
        <thead><tr><th>Team</th><th>Agent</th><th>Status</th></tr></thead>
        <tbody>
          {run.stages.map((s) => (
            <tr key={s.agent}>
              <td>{s.team}</td><td>{s.title}</td>
              <td className={s.status === "done" ? "up" : s.status === "error" ? "down" : "muted"}>{STATUS_TEXT[s.status] || s.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Decision({ brief }) {
  const rep = brief.reports || {};
  const d = rep.decision;
  const snap = brief.snapshot || {};
  const trader = rep.trader;
  return (
    <div className="cardbox" style={{ marginTop: 16 }}>
      <h3 className="sub-title" style={{ marginTop: 0 }}>Portfolio manager's decision</h3>
      {d ? (
        <>
          <p className="lede">
            Rating: <strong className={RATING_CLASS[String(d.rating)] || ""}>{d.rating_label || "withheld (no grounded evidence)"}</strong>
            {" · "}Trader's proposal: <strong>{PROPOSAL_TEXT[trader?.proposal] || "none"}</strong> ({d.proposal_verdict === "approve" ? "approved" : "rejected"} on paper)
            {" · "}Time horizon: {rep.time_horizon}
          </p>
          {d.executive_summary && <p><b>Executive summary.</b> {d.executive_summary}</p>}
          {d.investment_thesis && <p><b>Investment thesis.</b> {d.investment_thesis}</p>}
          <h4>Evidence</h4><Points items={d.evidence} />
          <h4>Key risks</h4><Points items={d.key_risks} />
        </>
      ) : (
        <p className="empty">No final decision in this brief ({rep.status}). {rep.stopped || ""}</p>
      )}
      <p className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>
        Written {brief.ts ? clock(brief.ts) : "—"} from the {snap.technical?.bar_hhmm || "latest"} candle
        ({snap.meta?.technical_source || "no technical read"}) · {(rep.calls || []).length} model calls in {num(rep.duration_s, 0)} s
        · list-price cost ${num(brief.cost_usd, 3)} · {rep.backend === "claude_cli" ? "Claude CLI" : "Anthropic API"} · status {rep.status}
      </p>
    </div>
  );
}

function Reports({ brief }) {
  const rep = brief.reports || {};
  const plan = rep.investment_plan;
  const trader = rep.trader;
  return (
    <>
      <h3 className="sub-title">Analyst team</h3>
      <div style={GRID}>
        {Object.entries(rep.analysts || {}).map(([key, a]) => (
          <div className="cardbox" key={key}>
            <h4 style={{ display: "flex", justifyContent: "space-between", margin: 0 }}>{a.title} <Stance value={a.report?.stance} /></h4>
            {a.report ? <><p>{a.report.summary}</p><Points items={a.report.points} /></> : <p className="empty">This analyst didn't return a report.</p>}
          </div>
        ))}
      </div>

      <h3 className="sub-title">Research team</h3>
      {(rep.debate || []).map((round) => (
        <div style={GRID} key={round.round}>
          {["bull", "bear"].map((side) => (
            <div className="cardbox" key={side}>
              <h4 style={{ margin: 0 }} className={side === "bull" ? "up" : "down"}>{side === "bull" ? "Bull" : "Bear"} researcher (round {round.round})</h4>
              {round[side] ? (
                <>
                  <p>{round[side].thesis}</p>
                  <Points items={round[side].points} />
                  {round[side].rebuttal && <p className="muted"><b>Rebuttal.</b> {round[side].rebuttal}</p>}
                </>
              ) : <p className="empty">No case returned.</p>}
            </div>
          ))}
        </div>
      ))}
      <div className="cardbox" style={{ marginTop: 12 }}>
        <h4 style={{ margin: 0 }}>Research manager's investment plan{plan?.rating_label ? `: ${plan.rating_label}` : ""}</h4>
        {plan ? (
          <>
            <p>{plan.summary}</p>
            <h4>Evidence</h4><Points items={plan.evidence} />
            <h4>Key risks</h4><Points items={plan.key_risks} />
            <h4>What would change the view</h4><Points items={plan.what_would_change_view} />
          </>
        ) : <p className="empty">No investment plan in this brief.</p>}
      </div>

      <h3 className="sub-title">Trader</h3>
      <div className="cardbox">
        {trader ? (
          <>
            <p className="lede"><strong>{PROPOSAL_TEXT[trader.proposal]}</strong>
              {trader.stop != null && <> · entry {num(trader.entry)}, stop {num(trader.stop)}, target {num(trader.target)} (the checklist's own levels)</>}
            </p>
            <p>{trader.rationale}</p>
            <Points items={trader.points} />
          </>
        ) : <p className="empty">No proposal in this brief.</p>}
      </div>

      <h3 className="sub-title">Risk management team</h3>
      <div style={GRID}>
        {Object.entries(rep.risk?.team || {}).map(([key, v]) => (
          <div className="cardbox" key={key}>
            <h4 style={{ display: "flex", justifyContent: "space-between", margin: 0 }}>{v.title} <Stance value={v.view?.stance} /></h4>
            {v.view ? <><p>{v.view.summary}</p><Points items={v.view.points} /></> : <p className="empty">No view returned.</p>}
          </div>
        ))}
      </div>
      {(rep.risk?.deterministic || []).length > 0 && (
        <div className="cardbox" style={{ marginTop: 12 }}>
          <h4 style={{ margin: 0 }}>Risk flags computed in code</h4>
          <ul className="evidence">
            {rep.risk.deterministic.map((f, i) => (
              <li key={i}>
                <span></span>
                <span><span className={`pill ${f.severity === "high" ? "short" : "wait"}`}>{f.severity}</span> {f.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {((rep.rejected || []).length > 0 || (rep.errors || []).length > 0) && (
        <details style={{ marginTop: 12 }}>
          <summary>
            {(rep.rejected || []).length} statement(s) dropped for citing data the snapshot doesn't contain
            {(rep.errors || []).length ? `, ${rep.errors.length} agent error(s)` : ""}
          </summary>
          <ul className="evidence">
            {(rep.rejected || []).map((r, i) => (
              <li key={`r${i}`}>
                <span></span>
                <span><b>{r.agent}</b> — {r.text} <span className="muted">({r.reason})</span></span>
              </li>
            ))}
            {(rep.errors || []).map((e, i) => (
              <li key={`e${i}`}>
                <span></span>
                <span><b className="down">{e.agent}</b> — {e.error}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

/**
 * The stock page's Research desk tab: TradingAgents-style analysts, researchers,
 * trader, risk team and portfolio manager, written by research_desk.py.
 * Research only — nothing here places an order or feeds a trading gate.
 */
export default function ResearchDesk({ symbol, watchlist }) {
  const [status, setStatus] = useState(null);
  const [briefs, setBriefs] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const wasRunning = useRef(false);

  const loadBriefs = useCallback(async () => {
    try { setBriefs(await call(`/api/research/briefs/${encodeURIComponent(symbol)}?limit=3`)); }
    catch (e) { setBriefs([]); setMessage(String(e.message || e)); }
  }, [symbol]);

  const loadStatus = useCallback(async () => {
    try {
      const st = await call("/api/research/status");
      setStatus(st);
      if (wasRunning.current && !st.run?.running) loadBriefs();
      wasRunning.current = !!st.run?.running;
    } catch (e) { setMessage(String(e.message || e)); }
  }, [loadBriefs]);

  useEffect(() => { setBriefs(null); loadStatus(); loadBriefs(); }, [symbol, loadStatus, loadBriefs]);
  useEffect(() => {
    const id = setInterval(loadStatus, status?.run?.running ? 3000 : 15000);
    return () => clearInterval(id);
  }, [loadStatus, status?.run?.running]);

  async function act(fn) {
    setBusy(true); setMessage("");
    try { await fn(); } catch (e) { setMessage(String(e.message || e)); }
    setBusy(false);
    loadStatus();
  }

  const toggle = () => act(async () => setStatus(await call("/api/research/enable", { enabled: !status.enabled })));
  const run = (symbols) => act(async () => setMessage((await call("/api/research/run", { symbols })).message));

  if (!status) return <p className="empty">Loading the research desk…</p>;
  const running = status.run?.running;
  const latest = briefs && briefs[0];

  return (
    <>
      <p className="lede" style={{ marginTop: 0 }}>
        A research desk modeled on a trading firm: four analysts, a bull and a bear researcher, a research manager,
        a trader, three risk analysts and a portfolio manager. <b>Research only</b> — it never places an order, and its
        rating gets no weight in any trade until it proves itself (below).
      </p>
      <div className="rb-row">
        <div className="rb-chip"><b>Model access</b><span>{status.backend_label || "None available"}</span></div>
        <div className="rb-chip"><b>Briefs today</b><span>{status.briefs_today} of {status.daily_brief_limit}</span></div>
        <div className="rb-chip"><b>List-price cost today</b><span>${num(status.cost_usd_today, 2)} of ${num(status.daily_cost_limit_usd, 0)}</span></div>
        <div className="rb-chip"><b>Calls per brief</b><span>{status.calls_per_brief}</span></div>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "12px 0" }}>
        <button className={`btn ${status.enabled ? "" : "primary"}`} disabled={busy || !status.backend} onClick={toggle}>
          {status.enabled ? "Switch the desk off" : "Switch the desk on"}
        </button>
        <button className="btn primary" disabled={busy || running || !!status.blocked_reason} onClick={() => run([symbol])}>
          Research {symbol}
        </button>
        <button className="btn" disabled={busy || running || !!status.blocked_reason || !(watchlist || []).length}
          onClick={() => run(watchlist)}>
          Research the watchlist ({(watchlist || []).length})
        </button>
      </div>
      {status.blocked_reason && <p className="muted">{status.blocked_reason}</p>}
      {status.backend === "claude_cli" && (
        <p className="muted" style={{ fontSize: 12.5 }}>
          Uses the Claude Code CLI on your Claude plan, so each brief counts toward your plan's usage.
          A brief takes a few minutes.
        </p>
      )}
      {message && <p className="muted">{message}</p>}
      {running && (
        <p className="lede">
          Researching {status.run.current || "…"} ({status.run.done.length} of {status.run.symbols.length} done)
        </p>
      )}
      <Progress run={status.run} symbol={symbol} />

      {briefs === null ? <p className="empty">Loading briefs…</p>
        : !latest ? <p className="empty">No brief for {symbol} yet.</p>
        : <><Decision brief={latest} /><Reports brief={latest} /></>}

      <p className="muted" style={{ fontSize: 12.5, marginTop: 16 }}>
        <b>Does the rating work?</b> {status.rating_ic?.note}
      </p>
    </>
  );
}
