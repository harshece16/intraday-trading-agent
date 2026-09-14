import { useEffect, useState } from "react";
import { apiFetch, apiJson } from "../api";
import { num } from "../format";

/** Live usage check + on/off toggle for the LLM news-sentiment feature. */
export default function LlmSentimentPanel() {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try { setStatus(await apiJson("/api/llm-sentiment/status")); } catch (e) { /* backend not reachable yet */ }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000); // live check — real usage, not a one-time page-load snapshot
    return () => clearInterval(id);
  }, []);

  async function toggle() {
    setBusy(true);
    try {
      const res = await apiFetch("/api/llm-sentiment/enable", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !status.enabled }),
      });
      if (res.ok) setStatus(await res.json());
      else alert((await res.json()).detail || "Couldn't change that.");
    } catch (e) { /* backend not reachable yet */ }
    setBusy(false);
  }

  if (!status) return <p className="empty">Loading LLM sentiment status…</p>;

  const pctOfBudget = status.daily_limit ? Math.round((status.used_today / status.daily_limit) * 100) : 0;

  return (
    <div className="cardbox" style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div>
          <b style={{ fontSize: 13.5 }}>LLM news sentiment (Claude Haiku 4.5)</b>
          <div className="detail" style={{ marginTop: 2 }}>
            {status.configured ? (status.enabled ? "ON" : "OFF") : "No ANTHROPIC_API_KEY set — nothing to turn on yet"}
          </div>
        </div>
        {status.configured && (
          <button className={`btn ${status.enabled ? "primary" : ""}`} disabled={busy} onClick={toggle}>
            {status.enabled ? "Turn off" : "Turn on"}
          </button>
        )}
      </div>
      {status.configured && (
        <div className="rb-row" style={{ marginTop: 12 }}>
          <div className="rb-chip">
            <b>Calls today</b>
            <span>{status.used_today} / {status.daily_limit} ({pctOfBudget}%)</span>
          </div>
          <div className="rb-chip">
            <b>Tokens today</b>
            <span>{num(status.input_tokens_today, 0)} in / {num(status.output_tokens_today, 0)} out</span>
          </div>
          <div className="rb-chip">
            <b>Actual cost today</b>
            <span>${status.estimated_cost_usd_today.toFixed(4)}</span>
          </div>
          <div className="rb-chip">
            <b>If the daily budget fills up</b>
            <span>{status.estimated_cost_usd_at_daily_limit != null ? `~$${status.estimated_cost_usd_at_daily_limit.toFixed(2)}/day` : "not enough calls yet to project"}</span>
          </div>
        </div>
      )}
      <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
        Cost is computed from the real input/output token counts each API call reports, at Haiku 4.5's published rate
        ($1/M input, $5/M output, verified against anthropic.com/claude/haiku) — not a per-call estimate. Headlines
        are cached permanently once scored, so the same story never gets billed twice.
      </p>
    </div>
  );
}
