import { postJson, useAction, useApi } from "../api";
import LoadState from "./LoadState";
import { num } from "../format";

/** Live usage check + on/off toggle for the LLM news-sentiment feature. */
export default function LlmSentimentPanel() {
  // Live check — real usage, not a one-time page-load snapshot. A failed load
  // shows its reason (#237); it used to read "Loading…" forever.
  const q = useApi("/api/llm-sentiment/status", 15000);
  const status = q.data;
  const toggleAction = useAction(async () => q.setData(await postJson("/api/llm-sentiment/enable", { enabled: !status.enabled })));
  const busy = toggleAction.busy;
  const toggle = toggleAction.run;

  if (!status) return <LoadState error={q.error && `LLM sentiment status: ${q.error}`} onRetry={q.reload} label="Loading LLM sentiment status…" />;

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
            {busy ? "Switching…" : status.enabled ? "Turn off" : "Turn on"}
          </button>
        )}
      </div>
      {toggleAction.error && <p className="down" role="alert" style={{ margin: "8px 0 0", fontSize: 13 }}>Couldn't switch it: {toggleAction.error}.</p>}
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
