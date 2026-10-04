import { Link } from "react-router-dom";
import { sendTelegramTest, setTelegramEnabled, useAction, useApi } from "../api";
import { inr } from "../format";
import { enabled as alertsEnabled, supported as alertsSupported } from "../notifications";
import { scorecardSummary, useEngineControls } from "../useEngineControls";
import { StatusPill } from "./Pill";

/** A fact that loads on its own: "…" while loading, the reason and a retry if it failed (#237). */
function Loaded({ q, children }) {
  if (q.data) return children(q.data);
  if (q.error) {
    return (
      <span className="down" style={{ fontWeight: 400 }}>
        Couldn't load: {q.error}.{" "}
        <button className="more inline" onClick={q.reload}>Try again</button>
      </span>
    );
  }
  return <span className="muted">Loading…</span>;
}

/** The intraday engine's control card: Paper/Live, pause, the kill switch. */
export default function AutonomyCard({ s }) {
  const c = useEngineControls(s);
  const fnoQ = useApi("/api/fno/status");
  const telegramQ = useApi("/api/alerts/telegram");
  // Read once here; Go live reads it again at the click.
  const summaryQ = useApi("/api/journal/summary");
  const scorecard = summaryQ.data?.scorecard || null;

  const telegramToggle = useAction(async () => telegramQ.setData(await setTelegramEnabled(!telegramQ.data.enabled)));
  const telegramTest = useAction(async () => {
    const r = await sendTelegramTest();
    if (!r.ok) throw new Error(r.error || "Telegram didn't accept it");
    return r;
  });

  const live = c.live;
  const capital = s.risk_total_capital;      // whatever's actually sizing trades right now
  const realCapital = s.real_capital;        // the Kite balance, or null until it has synced
  const usingPaperFigure = !live && capital !== realCapital;
  const anyBusy = c.busy.live || c.busy.paper;

  return (
    <section className="cardbox controls" style={{ borderColor: live ? "var(--short)" : undefined }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 className="h" style={{ fontSize: 17 }}>
            {live ? "Trading is live, running on its own" : "Paper trading: no real orders"}
          </h2>
          <div className="detail" style={{ marginTop: 2 }}>
            {live
              ? "The engine places real orders on its own rules, with no per-trade confirmation."
              : `Every order is simulated. The paper engine takes its trades automatically; the confidence gate ` +
                `(${s.live_confidence_bar ?? 60}/100) applies in Live only. Going live hands the engine real orders ` +
                `with no per-trade confirmation.`}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn" disabled={c.busy.pause} onClick={c.togglePause}
            title={`Stop opening new positions. Stops, targets and the ${s.square_off_time || "15:08"} square-off keep running.`}>
            {c.busy.pause ? (c.pausing ? "Pausing…" : "Resuming…") : s.entries_paused ? "Resume entries" : "Pause entries"}
          </button>
          {/* Disabled only by its own request: nothing else can lock out the kill switch (#233). */}
          <button className="btn danger" disabled={c.busy.stop} onClick={c.killSwitch}
            title="Pause entries, close every open position at market, switch to Paper">
            {c.busy.stop ? "Stopping…" : "Stop & close all"}
          </button>
          <button className={`btn ${live ? "" : "primary"}`} disabled={anyBusy} onClick={live ? c.goPaper : c.goLive}>
            {anyBusy ? "Switching…" : live ? "Switch to Paper" : "Go live"}
          </button>
        </div>
      </div>
      <p className="detail" role="status" aria-live="polite" style={{ margin: c.result ? "10px 0 0" : 0 }}>
        {c.result && <span className={c.result.tone}>{c.result.text}</span>}
      </p>
      {s.entries_paused && (
        <p className="note" style={{ margin: "12px 0 0", background: "var(--wait-bg)", color: "var(--wait)" }}>
          New entries are paused. Open positions still have their stops, targets and the {s.square_off_time || "15:08"} square-off.
        </p>
      )}
      <dl className="facts controls-facts">
        <div><dt>{usingPaperFigure ? "Paper capital" : "Real capital"}</dt><dd>{inr(capital)}</dd></div>
        {usingPaperFigure && (
          <div>
            <dt>Real Kite balance</dt>
            <dd>{realCapital == null ? <span className="muted">Not synced yet. Connect Kite first.</span> : inr(realCapital)}</dd>
          </div>
        )}
        <div><dt>F&amp;O (options)</dt><dd><Loaded q={fnoQ}>{(f) => (f.enabled ? "On" : "Off")}</Loaded></dd></div>
        <div>
          <dt>Telegram alerts</dt>
          <dd>
            <Loaded q={telegramQ}>
              {(t) => (!t.configured ? <span className="muted">Not set up</span> : (
                <>
                  {t.enabled ? "On" : "Off"}{" "}
                  <button className="more inline" disabled={telegramToggle.busy} onClick={telegramToggle.run}>
                    {telegramToggle.busy ? "…" : t.enabled ? "turn off" : "turn on"}
                  </button>{" "}
                  <button className="more inline" disabled={telegramTest.busy} onClick={telegramTest.run}>
                    {telegramTest.busy ? "sending…" : telegramTest.error ? "test again" : "test"}
                  </button>
                </>
              ))}
            </Loaded>
          </dd>
          {telegramToggle.error && <dd className="down" role="alert" style={{ fontSize: 12, fontWeight: 400 }}>Couldn't change Telegram alerts: {telegramToggle.error}.</dd>}
          {telegramTest.error && <dd className="down" role="alert" style={{ fontSize: 12, fontWeight: 400 }}>Test failed: {telegramTest.error}.</dd>}
          {telegramQ.data?.last_error && <dd className="down" style={{ fontSize: 12, fontWeight: 400 }}>Last send failed: {telegramQ.data.last_error}</dd>}
        </div>
        <div><dt>Browser alerts</dt><dd>{alertsSupported() ? (alertsEnabled() ? "On" : <span className="muted">Off</span>) : "—"}</dd></div>
        <div>
          <dt>Proven edge</dt>
          <dd>
            <Loaded q={summaryQ}>
              {() => (scorecard
                ? <StatusPill status={scorecard.some((r) => r.status === "fail") ? "fail" : scorecard.every((r) => r.status === "pass") ? "pass" : "pending"} />
                : <span className="muted">—</span>)}
            </Loaded>
          </dd>
        </div>
      </dl>
      {scorecard && scorecard.some((r) => r.status === "fail") && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          {scorecardSummary(scorecard)}{" "}
          <Link className="more" to="/journal">See the full Scorecard →</Link>
        </p>
      )}
      {usingPaperFigure && capital != null && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          Paper mode sizes trades against a fixed {inr(capital)} test figure (config.RISK.paper_capital)
          {realCapital != null ? `, not your real ${inr(realCapital)} Kite balance` : ""}. Going live sizes them on the
          real Kite balance at once.
        </p>
      )}
      {live && capital != null && capital < 2000 && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          At {inr(capital)}, the 1% risk model sizes most stocks to 0 shares — expect few or no
          cash-equity trades until the account is funded further.{" "}
          <Link className="more" to="/day-plan">See exactly which picks would size →</Link>
        </p>
      )}
    </section>
  );
}
