import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { clock, money, num } from "../format";
import { SidePill } from "./Pill";
import SymLink from "./SymLink";

// Manual review queue (backend/review_queue.py). The engine offers setups that
// missed its entry by exactly one gate; nothing is placed until you approve.

async function post(path, body) {
  const res = await apiFetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}),
  });
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON error */ }
  if (!res.ok) return { ok: false, reason: data?.detail || `HTTP ${res.status}` };
  return data;
}

const pct0 = (x) => (x == null ? "—" : `${Math.round(x * 100)}%`);

// What the card would have done had it been approved (review_queue.shadow_outcome).
const SHADOW_WORD = { open: "Open", stopped: "Stopped", target: "Target hit", squared_off: "Squared off" };

function ShadowText({ sh }) {
  if (!sh || sh.net_rs == null) return <span className="muted">—</span>;
  const when = sh.exit_ts ? ` ${clock(sh.exit_ts)}` : "";
  const at = sh.status === "open" ? ` at ${num(sh.mark_price)}` : ` @ ${num(sh.exit_price)}`;
  return (
    <span className={sh.net_rs > 0 ? "up" : sh.net_rs < 0 ? "down" : ""}>
      {SHADOW_WORD[sh.status] || sh.status}{when}{at}: {money(sh.net_rs)} ({sh.r > 0 ? "+" : ""}{num(sh.r)}R)
      {sh.status !== "open" && !sh.final && <span className="muted"> (provisional)</span>}
    </span>
  );
}

// Display only: the backend is the authority on expiry and refuses a late
// approval whatever this shows.
function useNow() {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function Countdown({ expiresTs }) {
  const now = useNow();
  const left = Math.max(0, Math.round(expiresTs - now));
  const m = Math.floor(left / 60), sec = String(left % 60).padStart(2, "0");
  return <span className={left < 60 ? "down" : "muted"}>{left ? `${m}:${sec} left` : "expiring…"}</span>;
}

function PendingCard({ c, live }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  async function approve() {
    let body = {};
    if (live) {
      const ok = confirm(
        `REAL MONEY — this places a real Kite order.\n\n` +
        `${c.side === "LONG" ? "BUY" : "SELL (short, intraday)"} about ${c.qty} ${c.symbol} at the live price, ` +
        `stop ${num(c.stop)}, target ${num(c.target)}.\nRisk ≈ ${money(-c.risk_rs)}, reward ≈ ${money(c.reward_rs)}, ` +
        `costs ≈ ${money(-c.cost_rs)}.\n\n` +
        `The engine skipped this because it failed "${c.blocker.label}". ${c.verdict}\n\nPlace it?`,
      );
      if (!ok) return;
      body = { confirm_live: true };
    }
    setBusy(true);
    const r = await post(`/api/review-queue/${c.id}/approve`, body);
    setBusy(false);
    setMsg(r.ok ? `Placed: ${r.qty} @ ${num(r.fill_price)} (R:R ${num(r.net_rrr_at_fill)} at the fill)` : r.reason);
  }

  async function reject() {
    setBusy(true);
    const r = await post(`/api/review-queue/${c.id}/reject`);
    setBusy(false);
    if (!r.ok) setMsg(r.reason);
  }

  const conf = c.confidence;
  return (
    <div className="cardbox" style={{ marginTop: 10, borderColor: live ? "var(--short)" : undefined }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
          <SidePill side={c.side} />
          <b><SymLink sym={c.symbol} /></b>
          <span className="muted">{c.setup}</span>
          {live && <span className="pill short">LIVE — real money</span>}
        </div>
        <Countdown expiresTs={c.expires_ts} />
      </div>
      <p style={{ margin: "8px 0 4px", fontSize: 13.5 }}>
        Skipped because it failed only <b>{c.blocker.label}</b>: <span className="muted">{c.blocker.detail}</span>
      </p>
      <div className="rb-row" style={{ marginTop: 8 }}>
        <div className="rb-chip"><b>Entry / stop / target</b><span>{num(c.entry)} / {num(c.stop)} / {num(c.target)}</span></div>
        <div className="rb-chip"><b>R:R after costs</b><span className={c.net_rrr < 1 ? "down" : ""}>{num(c.net_rrr)}</span></div>
        <div className="rb-chip"><b>Size</b><span>{c.qty} shares</span></div>
        <div className="rb-chip"><b>Risk / reward</b><span>{money(-c.risk_rs)} / {money(c.reward_rs)}</span></div>
        <div className="rb-chip"><b>Costs</b><span>{money(-c.cost_rs)} ({num(c.friction)}× of the stop)</span></div>
        <div className="rb-chip">
          <b>Needs to win</b>
          <span className={c.breakeven_win_rate == null || c.breakeven_win_rate > c.reference_win_rate ? "down" : "up"}>
            {c.breakeven_win_rate == null ? "can't break even" : pct0(c.breakeven_win_rate)} vs {pct0(c.reference_win_rate)} measured
          </span>
        </div>
        <div className="rb-chip"><b>Expected per trade</b><span className={c.expected_r < 0 ? "down" : "up"}>{c.expected_r > 0 ? "+" : ""}{num(c.expected_r)}R</span></div>
        {conf && (
          <div className="rb-chip"><b>Confidence</b><span>{conf.score}/100 (bar {conf.bar}; setup {conf.local} × {num(conf.multiplier)})</span></div>
        )}
      </div>
      <p className="muted" style={{ margin: "8px 0 0", fontSize: 12.5 }}>
        {c.verdict} Measured on {c.reference_source}.
      </p>
      {c.shadow && (
        <p className="detail" style={{ margin: "6px 0 0" }}>
          If you'd approved it when it was offered: <ShadowText sh={c.shadow} />
        </p>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button className="btn primary" disabled={busy} onClick={approve}>{busy ? "…" : live ? "Approve — real order" : "Approve (paper)"}</button>
        <button className="btn" disabled={busy} onClick={reject}>Reject</button>
        {msg && <span className="detail">{msg}</span>}
      </div>
    </div>
  );
}

const STATUS_TEXT = {
  approved: "approved", rejected: "rejected", expired: "expired", refused: "couldn't be placed", failed: "order failed",
};

function DecidedRow({ c }) {
  const o = c.outcome || {};
  const detail = c.status === "approved"
    ? `${o.qty} @ ${num(o.fill_price)}, R:R ${num(o.net_rrr_at_fill)}${o.mode === "live" ? " — LIVE" : ""}`
    : o.reason || "";
  return (
    <tr>
      <td>{clock(c.decided_ts || c.created_ts)}</td>
      <td><SymLink sym={c.symbol} /></td>
      <td><SidePill side={c.side} /></td>
      <td>{c.blocker?.label}</td>
      <td className={c.status === "approved" ? "up" : c.status === "refused" || c.status === "failed" ? "down" : "muted"}>
        {STATUS_TEXT[c.status] || c.status}
      </td>
      <td>{c.status === "approved" ? <span className="muted">real trade</span> : <ShadowText sh={c.shadow} />}</td>
      <td className="detail">{detail}</td>
    </tr>
  );
}

export default function ReviewQueue({ s }) {
  const rq = s.review_queue;
  const [busy, setBusy] = useState(false);
  if (!rq) return null;
  const live = !s.paper_mode;
  const pending = rq.cards.filter((c) => c.status === "pending");
  const decided = rq.cards.filter((c) => c.status !== "pending");

  async function toggle() {
    if (!rq.enabled) {
      const ok = confirm(
        "Turn on the manual review queue?\n\n" +
        "Setups that miss the entry by exactly ONE rule will be shown to you to approve or reject. " +
        "Approving overrides that one rule (and the confidence gate); every risk limit still applies.\n\n" +
        "These are the setups the rules were built to skip: in backtests, trades the R:R rule rejects averaged " +
        "−1.17R each (README §48). Each card shows the win rate its trade would need against the 32% this " +
        "checklist actually wins." + (live ? "\n\nYou are in LIVE mode — approvals place real orders." : ""),
      );
      if (!ok) return;
    }
    setBusy(true);
    await post("/api/review-queue/enable", { enabled: !rq.enabled });
    setBusy(false);
  }

  return (
    <div className="cardbox" style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 className="h" style={{ fontSize: 16 }}>
            Review queue {rq.enabled ? `— on${pending.length ? `, ${pending.length} waiting` : ""}` : "— off"}
          </h2>
          <div className="detail" style={{ marginTop: 2 }}>
            {rq.enabled
              ? `Setups that failed exactly one rule appear here for ${Math.round(rq.expiry_seconds / 60)} minutes. Nothing is placed unless you approve.`
              : "Off: setups that fail a rule are skipped, as usual. Turn it on to decide on near-misses yourself."}
          </div>
        </div>
        <button className="btn" disabled={busy} onClick={toggle}>{busy ? "…" : rq.enabled ? "Turn off" : "Turn on"}</button>
      </div>
      {pending.map((c) => <PendingCard key={c.id} c={c} live={live} />)}
      {rq.enabled && !pending.length && <p className="empty" style={{ marginTop: 10 }}>Nothing waiting right now.</p>}
      {decided.length > 0 && (
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table className="datatable">
            <thead><tr><th>Time</th><th>Stock</th><th>Side</th><th>Failed</th><th>Decision</th><th>If approved</th><th></th></tr></thead>
            <tbody>{decided.map((c) => <DecidedRow key={c.id} c={c} />)}</tbody>
          </table>
        </div>
      )}
      {rq.shadow_summary?.trades > 0 && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          If every card today that wasn't approved had been:{" "}
          <b className={rq.shadow_summary.net_rs > 0 ? "up" : rq.shadow_summary.net_rs < 0 ? "down" : ""}>
            {money(rq.shadow_summary.net_rs)} ({rq.shadow_summary.r > 0 ? "+" : ""}{num(rq.shadow_summary.r)}R)
          </b>{" "}
          across {rq.shadow_summary.trades} trade{rq.shadow_summary.trades > 1 ? "s" : ""}
          {rq.shadow_summary.open ? `, ${rq.shadow_summary.open} still open` : ""}
          {rq.shadow_summary.provisional ? `, ${rq.shadow_summary.provisional} provisional` : ""}. {rq.shadow_summary.basis}
        </p>
      )}
    </div>
  );
}
