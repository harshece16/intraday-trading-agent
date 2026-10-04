import { useState } from "react";
import { apiJson, explainRefusal, setEntriesPaused, setTradingMode, stopAndCloseAll, useAction } from "./api";
import { inr } from "./format";

/** The Dimaag Scorecard in one line, for the go-live warning and the control card. */
export function scorecardSummary(rows) {
  if (!rows || !rows.length) return "Dimaag Scorecard: couldn't be loaded. Check the Journal page before deciding.";
  const fails = rows.filter((r) => r.status === "fail").map((r) => r.criterion);
  const passes = rows.filter((r) => r.status === "pass").length;
  const pending = rows.length - fails.length - passes;
  if (fails.length) {
    return `Dimaag Scorecard: fails on ${fails.join(" and ")}. This system has not shown a proven edge.`;
  }
  if (passes === rows.length) return "Dimaag Scorecard: all criteria currently pass.";
  return `Dimaag Scorecard: ${passes} of ${rows.length} pass, ${pending} without enough data yet. No proven edge confirmed.`;
}

export function openPositionCount(s) {
  return Object.values(s?.positions || {}).filter((p) => p.quantity).length + Object.keys(s?.fno_positions || {}).length;
}

/** The go-live warning. Read fresh at the click, so the header's Live button
 *  and the Overview card's Go live say the same thing (#234). */
async function goLiveMessage(s) {
  const [summary, fno] = await Promise.allSettled([apiJson("/api/journal/summary", { timeoutMs: 20000 }), apiJson("/api/fno/status")]);
  const scorecard = summary.status === "fulfilled" ? summary.value?.scorecard : null;
  const fnoLine = fno.status === "fulfilled"
    ? `F&O: ${fno.value?.enabled ? "on" : "off"} (its own switch is on Portfolio).`
    : "F&O: couldn't be checked. Its own switch is on Portfolio.";
  const real = s.real_capital;
  const paperFigure = s.paper_mode && s.risk_total_capital != null && s.risk_total_capital !== real ? s.risk_total_capital : null;
  const balanceLine = real == null
    ? "Real Kite balance: not synced yet. Connect Kite first."
    : `Real Kite balance: ${inr(real)}. Trades are sized on this${paperFigure != null ? `, not the ${inr(paperFigure)} paper figure` : ""}.`;
  return [
    "Go live with the intraday engine?",
    `Research found no intraday edge: 202 trials found nothing that beats the ~16.6 bp (0.17%) round-trip cost. ${scorecardSummary(scorecard)}`,
    "In Live, the engine buys and sells on Zerodha by itself every ~30 seconds, with no per-trade confirmation, whether or not you're watching.",
    balanceLine,
    fnoLine,
    `New entries need confidence ${s.live_confidence_bar ?? 60}/100. Open paper positions stay paper.`,
    "Switch back to Paper here at any time; it takes effect at once. The momentum book isn't affected.",
  ].join("\n\n");
}

/**
 * Paper/Live, pause and the kill switch, shared by the header and the
 * intraday Overview card. Each control has its own busy state, so a hung
 * Pause or Go live can never disable Stop & close all (#233).
 */
export function useEngineControls(s) {
  const [result, setResult] = useState(null); // { tone: "up" | "down" | "", text }
  const [pausing, setPausing] = useState(null); // what a running Pause/Resume request asked for
  const live = s ? !s.paper_mode : false;

  const liveAction = useAction(async () => {
    const msg = await goLiveMessage(s);
    if (!confirm(msg)) return false;
    await setTradingMode(false);
    return true;
  });
  const paperAction = useAction(() => setTradingMode(true));
  const pauseAction = useAction((paused) => setEntriesPaused(paused));
  const stopAction = useAction(() => stopAndCloseAll());

  async function goLive() {
    if (liveAction.busy) return;
    setResult(null);
    const r = await liveAction.run();
    if (r.ok && r.value) setResult({ tone: "down", text: "Live. The engine now places real orders." });
    else if (!r.ok && !explainRefusal(r.error)) alert(`Couldn't go live: ${r.error.message}`);
  }

  async function goPaper() {
    if (paperAction.busy) return;
    setResult(null);
    const r = await paperAction.run();
    if (r.ok) setResult({ tone: "", text: "Back in Paper. No real orders from here on." });
    else alert(`Couldn't switch to Paper: ${r.error.message}`);
  }

  async function togglePause() {
    if (!s || pauseAction.busy) return;
    const pausing = !s.entries_paused;
    setResult(null);
    setPausing(pausing);
    const r = await pauseAction.run(pausing);
    if (r.ok) setResult({ tone: "", text: pausing ? "Entries paused. Stops, targets and the square-off still run." : "Entries resumed." });
    else alert(`Couldn't ${pausing ? "pause" : "resume"} entries: ${r.error.message}`);
  }

  async function killSwitch() {
    if (!s || stopAction.busy) return;
    const n = openPositionCount(s);
    const msg = n
      ? `Stop the intraday engine and close its ${n} open position${n === 1 ? "" : "s"}?\n\n` +
        `This pauses new entries, closes ${n === 1 ? "it" : "them"} at market ` +
        `${live ? "with real orders on Zerodha" : "(paper fills; nothing is sent to Kite)"}, and switches to Paper. ` +
        "The momentum book isn't affected."
      : "Stop the intraday engine?\n\nNo position is open. This pauses new entries and switches to Paper. " +
        "The momentum book isn't affected.";
    if (!confirm(msg)) return;
    setResult(null);
    const r = await stopAction.run();
    if (!r.ok) {
      const after = r.error.timeout
        ? "It may still be closing positions. Check Open positions and the live log."
        : live ? "Close positions in Kite directly." : "Nothing was sent to Kite.";
      setResult({ tone: "down", text: `Stop & close all failed: ${r.error.message}. ${after}` });
      alert(`Stop & close all failed: ${r.error.message}. ${after}`);
      return;
    }
    const v = r.value || {};
    const closed = (v.closed || []).length;
    if (v.failed?.length) {
      const stillLive = v.paper_mode === false;
      const list = v.failed.map((f) => `${f.symbol} (${f.error})`).join(", ");
      setResult({ tone: "down", text: `Couldn't close ${list}. ${stillLive ? "Still in Live." : "Still in Paper."}` });
      alert(`Couldn't close: ${list}.\n\n${stillLive ? "Still in Live. Close these in Kite now." : "Still in Paper. Nothing was sent to Kite."}`);
      return;
    }
    setResult({
      tone: "",
      text: `Stopped: ${closed ? `closed ${closed} position${closed === 1 ? "" : "s"}, ` : ""}entries paused, now in Paper.`,
    });
  }

  return {
    live, result, goLive, goPaper, togglePause, killSwitch, pausing,
    busy: { live: liveAction.busy, paper: paperAction.busy, pause: pauseAction.busy, stop: stopAction.busy },
  };
}
