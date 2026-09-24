import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch, apiJson, explainRefusal, openKiteLogin, sendTelegramTest, setEntriesPaused, setTelegramEnabled, setTradingMode, stopAndCloseAll } from "../api";
import { clock, dateLabel, money, num, pct, tone } from "../format";
import { analysisFor, heldSymbols, isReady, primaryRule, scanRows } from "../helpers";
import { RuleTag } from "../components/RuleBook";
import { SidePill, StatusPill } from "../components/Pill";
import SymLink from "../components/SymLink";
import Feed from "../components/Feed";
import Chart from "../components/Chart";
import ReviewQueue, { ReviewQueueToggle } from "../components/ReviewQueue";
import { enabled as alertsEnabled, supported as alertsSupported } from "../notifications";


const ONBOARD_KEY = "sahab_onboarding_dismissed";

function OnboardingBanner({ s }) {
  const [showSteps, setShowSteps] = useState(false);
  const [dismissed, setDismissed] = useState(() => {
    try { return localStorage.getItem(ONBOARD_KEY) === "1"; } catch (e) { return false; }
  });

  useEffect(() => {
    if (s?.kite_connected) {
      try { localStorage.setItem(ONBOARD_KEY, "1"); } catch (e) { /* ignore */ }
      setDismissed(true);
    }
  }, [s?.kite_connected]);

  if (dismissed || s?.kite_connected) return null;

  function dismiss() {
    try { localStorage.setItem(ONBOARD_KEY, "1"); } catch (e) { /* ignore */ }
    setDismissed(true);
  }

  // One line until asked: the steps matter once, the space matters every day.
  return (
    <div className="attention">
      <div className="attention-row">
        <span><b>First time here?</b> <span className="muted">Three things to do before you start.</span></span>
        <span className="attention-actions">
          <button className="btn" aria-expanded={showSteps} onClick={() => setShowSteps((v) => !v)}>{showSteps ? "Hide steps" : "Show steps"}</button>
          <button className="btn" onClick={dismiss}>Dismiss</button>
        </span>
      </div>
      {showSteps && (
        <ol className="attention-steps">
          <li><b>Connect Kite</b> — open the Paper ▾ menu at the top right and choose Connect Kite. Real prices, holdings and orders all need this; nothing trades without it.</li>
          <li><b>Confirm you're in Paper mode</b> — the same button says Paper or Live. Paper is the safe default and simulates everything; Live places real orders.</li>
          <li><b>Read the Dimaag Scorecard on the Journal page</b> before ever considering Live — it shows, honestly, whether this system has actually proven a real edge yet.</li>
        </ol>
      )}
    </div>
  );
}

/* Distinct from the onboarding banner above: that one teaches a new user and
   is dismissed forever once they connect. This one fires when a session that
   WAS working has died — the case that used to be invisible, because the
   header went on saying "Kite connected" and the engine quietly fell back to
   delayed prices. It can't be dismissed; it goes away when Kite comes back. */
function KiteSessionAlert({ s }) {
  const state = s?.kite_state;
  const stalled = !!s?.kite_login_stalled;
  if (!stalled && state !== "expired" && state !== "error") return null;
  const expired = state === "expired";
  const title = stalled ? "Kite login didn't come back"
    : expired ? "Kite session expired" : "Kite isn't reachable";
  return (
    <div className="cardbox" style={{ marginBottom: 20, borderColor: "var(--short)" }} role="alert">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <h2 className="h" style={{ fontSize: 16, color: "var(--short)" }}>{title}</h2>
          <p style={{ margin: "6px 0 0", fontSize: 13.5, lineHeight: 1.7 }}>
            {s.kite_reason}{" "}
            {expired && !stalled && "Until you reconnect, prices come from the delayed free feed and no live order can be placed."}
          </p>
          {/* The half of the round trip the app can't see from inside: which
              URL Zerodha will send the browser back to. A mismatch here looks
              identical to "the button did nothing". */}
          {s.kite_redirect_url && (
            <p style={{ margin: "8px 0 0", fontSize: 12.5, lineHeight: 1.7, color: "var(--ink-2)" }}>
              Zerodha must redirect back to{" "}
              <code style={{ wordBreak: "break-all" }}>{s.kite_redirect_url}</code>{" "}
              — register that exact URL at{" "}
              <a href="https://developers.kite.trade" target="_blank" rel="noreferrer">developers.kite.trade</a>
              {stalled && ", and make sure whatever it points at is running right now"}.
            </p>
          )}
        </div>
        <button
          className="btn primary"
          onClick={openKiteLogin}
        >
          {stalled ? "Try again" : "Reconnect"}
        </button>
      </div>
    </div>
  );
}

function scorecardSummary(rows) {
  if (!rows || !rows.length) return "Dimaag Scorecard: not loaded — check the Journal page before deciding.";
  const fails = rows.filter((r) => r.status === "fail").map((r) => r.criterion);
  const passes = rows.filter((r) => r.status === "pass").length;
  const pending = rows.length - fails.length - passes;
  if (fails.length) {
    return `Dimaag Scorecard: FAILS on ${fails.join(" and ")} — this system has NOT shown a proven edge yet.`;
  }
  if (passes === rows.length) return "Dimaag Scorecard: all criteria currently pass.";
  return `Dimaag Scorecard: ${passes}/${rows.length} pass, ${pending} not enough data yet — no proven edge confirmed yet.`;
}

function AutonomyCard({ s }) {
  const [fno, setFno] = useState(null);
  const [scorecard, setScorecard] = useState(null);
  const [busy, setBusy] = useState(false);
  const [telegram, setTelegram] = useState(null);

  useEffect(() => {
    let stopped = false;
    function load() {
      apiJson("/api/alerts/telegram").then((d) => !stopped && setTelegram(d)).catch(() => {});
      apiJson("/api/fno/status").then((d) => !stopped && setFno(d)).catch(() => {});
      apiJson("/api/journal/summary").then((d) => !stopped && setScorecard(d.scorecard)).catch(() => {});
    }
    load();
    const id = setInterval(load, 20000);
    return () => { stopped = true; clearInterval(id); };
  }, []);

  const live = !s.paper_mode;
  const capital = s.risk_total_capital;      // whatever's actually sizing trades right now
  const realCapital = s.real_capital;        // always the true Kite balance, regardless of mode
  const usingPaperFigure = !live && realCapital != null && capital !== realCapital;

  async function goLive() {
    const msg =
      `${scorecardSummary(scorecard)}\n\n` +
      `This turns on real order placement — Trader Sahab will buy and sell on Zerodha automatically from now on, ` +
      `every ~30 seconds, on its own rules, with no per-trade confirmation from you or anyone else. It runs whether ` +
      `or not you're watching.\n\n` +
      `Real capital right now: ₹${(realCapital ?? capital)?.toLocaleString("en-IN") ?? "—"} (synced from your Kite account` +
      `${usingPaperFigure ? " — NOT the paper figure below, sizing snaps to this the moment you go live" : ""}).\n` +
      `F&O (options): ${fno?.enabled ? "ON" : "OFF"} — turn it on separately from Portfolio if you want option trades too.\n\n` +
      `Turn it back to Paper any time from this same control — that takes effect immediately, no confirmation needed.\n\n` +
      `Go live now?`;
    if (!confirm(msg)) return;
    setBusy(true);
    try {
      await setTradingMode(false);
    } catch (e) {
      if (!explainRefusal(e)) alert(`Couldn't go live: ${e.message}`);
    }
    setBusy(false);
  }

  async function goPaper() {
    setBusy(true);
    try { await setTradingMode(true); } catch (e) { alert(`Couldn't switch to Paper: ${e.message}`); }
    setBusy(false);
  }

  async function toggleTelegram() {
    try { setTelegram(await setTelegramEnabled(!telegram.enabled)); } catch (e) { alert(`Couldn't change phone alerts: ${e.message}`); }
  }

  async function testTelegram() {
    const r = await sendTelegramTest().catch((e) => ({ ok: false, error: e.message }));
    alert(r.ok ? "Test alert sent — check Telegram." : `Telegram test failed: ${r.error}`);
  }

  async function togglePause() {
    setBusy(true);
    try { await setEntriesPaused(!s.entries_paused); } catch (e) { alert(`Couldn't change the pause: ${e.message}`); }
    setBusy(false);
  }

  const openCount = Object.values(s.positions || {}).filter((p) => p.quantity).length + Object.keys(s.fno_positions || {}).length;

  async function killSwitch() {
    const msg =
      `Stop trading and close everything?\n\n` +
      `This pauses new entries, closes all ${openCount} open position${openCount === 1 ? "" : "s"} at market ` +
      `${live ? "with real orders on Zerodha" : "(paper fills)"}, and switches to Paper.`;
    if (!confirm(msg)) return;
    setBusy(true);
    try {
      const r = await stopAndCloseAll();
      if (r.failed?.length) {
        alert(`Couldn't close: ${r.failed.map((f) => `${f.symbol} (${f.error})`).join(", ")}.\n\nStill LIVE — close these in Kite now.`);
      }
    } catch (e) {
      alert(`Kill switch failed: ${e.message}. Close positions in Kite directly.`);
    }
    setBusy(false);
  }

  return (
    <div className="cardbox" style={{ marginBottom: 20, borderColor: live ? "var(--short)" : undefined }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 className="h" style={{ fontSize: 16 }}>
            {live ? "Trading control — live, running automatically" : "Trading control — paper mode"}
          </h2>
          <div className="detail" style={{ marginTop: 2 }}>
            {live
              ? "The engine is placing real orders on its own rules, unattended. No action needed from you."
              : "Simulated orders only. Going live hands the engine real orders with no per-trade confirmation."}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn" disabled={busy} onClick={togglePause}
            title="Stop opening new positions. Stops, targets and the 15:15 square-off keep running.">
            {s.entries_paused ? "Resume entries" : "Pause entries"}
          </button>
          <button className="btn danger" disabled={busy} onClick={killSwitch}
            title="Pause entries, close every open position at market, switch to Paper">
            Stop &amp; close all
          </button>
          <button className={`btn ${live ? "" : "primary"}`} disabled={busy} onClick={live ? goPaper : goLive}>
            {busy ? "…" : live ? "Switch to Paper" : "Go live"}
          </button>
        </div>
      </div>
      {s.entries_paused && (
        <p className="note" style={{ margin: "12px 0 0", background: "var(--wait-bg)", color: "var(--wait)" }}>
          New entries are paused. Open positions still have their stops, targets and the 15:15 square-off.
        </p>
      )}
      {/* The detail below is reference, not a daily read: one summary line,
          with the full account, alert and scorecard detail a click away. */}
      <details className="more-panel">
        <summary>
          <span className="more-summary">
            {usingPaperFigure ? "Paper capital" : "Capital"} {capital != null ? `₹${num(capital, 0)}` : "—"} · F&amp;O {fno ? (fno.enabled ? "on" : "off") : "…"}
            {" · "}Phone alerts {!telegram ? "…" : !telegram.configured ? "not set up" : telegram.enabled ? "on" : "off"}
            {scorecard && <>{" · "}Proven edge <StatusPill status={scorecard.some((r) => r.status === "fail") ? "fail" : scorecard.every((r) => r.status === "pass") ? "pass" : "pending"} /></>}
          </span>
          <span className="more-toggle">Account &amp; alerts</span>
        </summary>
      <div className="rb-row" style={{ marginTop: 12 }}>
        <div className="rb-chip">
          <b>{usingPaperFigure ? "Paper capital (simulated)" : "Real capital"}</b>
          <span>{money(capital)}</span>
        </div>
        {usingPaperFigure && (
          <div className="rb-chip"><b>Real Kite balance</b><span>{money(realCapital)}</span></div>
        )}
        <div className="rb-chip"><b>F&amp;O (options)</b><span>{fno ? (fno.enabled ? "ON" : "OFF") : "…"}</span></div>
        <div className="rb-chip">
          <b>Phone alerts (Telegram)</b>
          <span>
            {!telegram ? "…" : !telegram.configured ? "Not set up — see README §66" : telegram.enabled ? "ON" : "Off"}
            {telegram?.last_error ? ` · last send failed: ${telegram.last_error}` : ""}
          </span>
        </div>
        {telegram?.configured && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn" onClick={toggleTelegram}>{telegram.enabled ? "Turn phone alerts off" : "Turn phone alerts on"}</button>
            <button className="btn" onClick={testTelegram}>Send test</button>
          </div>
        )}
        <div className="rb-chip"><b>Browser alerts</b><span>{alertsSupported() ? (alertsEnabled() ? "ON" : "Off — turn on from the Paper/Live menu, top right") : "Not supported in this browser"}</span></div>
        {s.review_queue && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div className="rb-chip"><b>Review queue</b><span>{s.review_queue.enabled ? "On — near-misses wait for your approval" : "Off"}</span></div>
            <ReviewQueueToggle s={s} />
          </div>
        )}
        {scorecard && (
          <div className="rb-chip">
            <b>Proven edge (Dimaag Scorecard)</b>
            <span><StatusPill status={scorecard.some((r) => r.status === "fail") ? "fail" : scorecard.every((r) => r.status === "pass") ? "pass" : "pending"} /></span>
          </div>
        )}
      </div>
      {scorecard && scorecard.some((r) => r.status === "fail") && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          {scorecardSummary(scorecard)}{" "}
          <Link className="more" to="/journal">See the full Scorecard →</Link>
        </p>
      )}
      {usingPaperFigure && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          Paper mode is sizing against a fixed ₹{capital.toLocaleString("en-IN")} test figure
          (config.RISK.paper_capital), not your real ₹{realCapital.toLocaleString("en-IN")} Kite balance — set this
          up so simulated trades actually get sized. Going live snaps sizing back to the real balance immediately.
        </p>
      )}
      </details>
      {live && capital != null && capital < 2000 && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          At ₹{capital.toLocaleString("en-IN")}, the 1% risk model sizes most stocks to 0 shares — expect few or no
          cash-equity trades until the account is funded further.{" "}
          <Link className="more" to="/day-plan">See exactly which picks would size →</Link>
        </p>
      )}
    </div>
  );
}

function heroCopy(s) {
  const m = s.market, sc = s.scanner;
  if (s.holiday) {
    return {
      lead: `Markets are shut today for ${s.holiday.name}.`,
      rest: `Trading resumes ${new Date(s.holiday.next_trading_day + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short" })}.`,
    };
  }
  if (!m) return { lead: "Reading the market for the first time…", rest: "Trader Sahab is downloading prices for all NIFTY 100 stocks. This takes about 30 seconds." };
  const lead = {
    "risk-off": "The market is weak, so Trader Sahab is looking for stocks to short.",
    "risk-on": "The market is strong, so Trader Sahab is looking for stocks to buy.",
    neutral: "The market is mixed, so Trader Sahab trades both sides on clear setups only.",
  }[m.bias] || "Reading the market.";
  const n = m.nifty;
  const closed = s.market_status !== "open";
  const sides = Object.values((sc && sc.active_sides) || {});
  const shorts = sides.filter((x) => x === "SHORT").length;
  const longs = sides.length - shorts;
  const held = heldSymbols(s).length;
  const sentences = [
    `NIFTY ${n.chg_pct >= 0 ? "rose" : "fell"} ${Math.abs(n.chg_pct).toFixed(2)}% ${closed ? `on ${dateLabel(m.session_date)}` : "today"} and ${m.breadth.dec} of ${m.breadth.adv + m.breadth.dec} stocks fell.`,
    sides.length ? `Tracking ${sides.length} stocks, ${shorts} to short and ${longs} to buy.` : "No stock passes every filter yet.",
    held ? `${held} open position${held > 1 ? "s" : ""}.` : "No open positions.",
  ];
  if (m.vix_high) sentences.push(`India VIX is high, so new positions are half size.`);
  if (closed) sentences.push("Trading resumes at 9:15.");
  return { lead, rest: sentences.join(" ") };
}

function PickCard({ s, r, held }) {
  const navigate = useNavigate();
  const ready = isReady(s, r);
  const why = (r.reasons || []).slice(0, 2).map((x) => x.text).join("; ");
  const rule = primaryRule(r);
  return (
    <button className="pickcard" onClick={() => navigate(`/stock/${encodeURIComponent(r.symbol)}`)}>
      <div className="row1">
        <span className="sym">{r.symbol}</span>
        <SidePill side={r.side} />
        {held.has(r.symbol) ? <span className="pill solid">Holding</span> : ready ? <span className="pill solid">Ready</span> : null}
      </div>
      <div className="why">{why}</div>
      <RuleTag text={rule} />
      <div className="row2"><span>Score {num(r.final_score, 0)}</span><span className={tone(r.chg_pct)}>{pct(r.chg_pct)}</span></div>
    </button>
  );
}

function MiniChartCard({ s, r, held }) {
  const navigate = useNavigate();
  const a = analysisFor(s, r.symbol);
  const b = a && a.b;
  const pos = s.positions[r.symbol];
  const side = r && r.side ? r.side.toLowerCase() : b && b.bias === "short" ? "short" : "long";
  const cl = b && b.checklist ? b.checklist[side] || b.checklist.long : null;
  const plan = b ? { support: b.support, resistance: b.resistance, vwap: b.vwap, cl, side } : null;

  let planLine;
  if (pos && pos.quantity) {
    planLine = (
      <>Holding {Math.abs(pos.quantity)} at {num(pos.avg_price)} — <span className={tone(pos.unrealized_pnl)}>{money(pos.unrealized_pnl)}</span></>
    );
  } else if (cl && cl.stop != null) {
    planLine = <>Entry near {num(cl.entry)} · stop {num(cl.stop)} · target {num(cl.target)}</>;
  } else if (b?.blockers?.length) {
    planLine = <span className="muted">Waiting on: {b.blockers[0]}</span>;
  } else {
    planLine = <span className="muted">Watching for a setup</span>;
  }

  return (
    <div className="cardbox mini-chart-card" onClick={() => navigate(`/stock/${encodeURIComponent(r.symbol)}`)} style={{ cursor: "pointer" }}>
      <div className="mini-chart-head">
        <span className="sym">{r.symbol}</span>
        <span style={{ display: "flex", gap: 6 }}>
          {held.has(r.symbol) ? <span className="pill solid">Holding</span> : null}
          <SidePill side={r.side} />
        </span>
      </div>
      <Chart symbol={r.symbol} plan={plan} position={pos} patterns={b?.patterns} barTime={b?.bar_time} trades={s.trades} className="mini-chart" compact />
      <div className="mini-chart-plan">{planLine}</div>
    </div>
  );
}

export default function Overview({ state: s }) {
  const [scanning, setScanning] = useState(false);
  const [scanLabel, setScanLabel] = useState("Scan now");
  const [view, setView] = useState("cards");

  async function triggerScan() {
    setScanning(true);
    setScanLabel("Scanning…");
    try {
      const res = await apiFetch(`/api/scan`, { method: "POST" });
      const data = await res.json();
      setScanLabel(data.started ? "Scan started" : "Already scanning");
    } catch (e) {
      setScanLabel("Engine offline");
    }
    setTimeout(() => { setScanning(false); setScanLabel("Scan now"); }, 8000);
  }

  const copy = heroCopy(s);
  const m = s.market, sc = s.scanner;
  const sectors = (sc && sc.sectors) || [];
  const sector = (x) => (x ? <>{x.industry} <span className={tone(x.chg_pct)}>{pct(x.chg_pct)}</span></> : "—");

  const rows = scanRows(s);
  const held = new Set(heldSymbols(s));
  const picks = rows.filter((r) => r.status === "ACTIVE" || held.has(r.symbol)).slice(0, 6);

  const heldEntries = Object.entries(s.positions).filter(([, p]) => p.quantity !== 0);

  return (
    <>
      {/* Only what needs you right now sits above the headline. */}
      <KiteSessionAlert s={s} />
      <ReviewQueue s={s} hideWhenIdle />
      <OnboardingBanner s={s} />
      <section className="hero">
        <h1>{copy.lead}</h1>
        <p>{copy.rest}</p>
        <div className="hero-foot">
          <dl className="facts">
            {m && (
              <>
                <div><dt>NIFTY 50</dt><dd>{num(m.nifty.ltp, 0)} <span className={tone(m.nifty.chg_pct)}>{pct(m.nifty.chg_pct, 2)}</span></dd></div>
                <div><dt>India VIX</dt><dd>{num(m.vix, 1)}</dd></div>
                <div><dt>Advancing</dt><dd><span className="up">{m.breadth.adv}</span> <span className="muted">of {m.breadth.adv + m.breadth.dec}</span></dd></div>
                <div><dt>Strongest sector</dt><dd>{sector(sectors[0])}</dd></div>
                <div><dt>Weakest sector</dt><dd>{sector(sectors[sectors.length - 1])}</dd></div>
              </>
            )}
          </dl>
          <div className="scan-cta">
            <button className="btn primary" disabled={scanning} onClick={triggerScan}>{scanLabel}</button>
            <small>{sc ? `Scanned ${sc.scanned} stocks at ${clock(sc.ts)}` : ""}</small>
          </div>
        </div>
      </section>

      <AutonomyCard s={s} />

      <div className="section-head">
        <div>
          <h2 className="h">Today's picks</h2>
          <p className="sub">Stocks Trader Sahab is watching for an entry, by scan score. <a className="more" href="/screener">Full ranked list →</a></p>
        </div>
        {picks.length > 0 && (
          <div className="segmented view-toggle" role="group" aria-label="Show picks as">
            <button aria-pressed={view === "cards"} onClick={() => setView("cards")}>Cards</button>
            <button aria-pressed={view === "charts"} onClick={() => setView("charts")}>Charts</button>
          </div>
        )}
      </div>
      {!picks.length ? (
        <p className="empty">The scan hasn't found a stock that passes every filter yet.</p>
      ) : view === "cards" ? (
        <div className="grid3">{picks.map((r) => <PickCard key={r.symbol} s={s} r={r} held={held} />)}</div>
      ) : (
        <>
          <div className="mini-chart-grid">
            {picks.map((r) => <MiniChartCard key={r.symbol} s={s} r={r} held={held} />)}
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Entry, stop and target lines are the checklist's plan, not a forecast. Latest session shown. Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView</a>.
          </p>
        </>
      )}

      <div className="section-gap grid2">
        <div>
          <h2 className="h">What Trader Sahab is doing</h2>
          <p className="sub">The last few scans, picks and trades.</p>
          <Feed items={(s.activity || []).slice(0, 6)} />
        </div>
        <div>
          <h2 className="h">Open positions</h2>
          <div className="cardbox">
            {heldEntries.length ? (
              <div className="positions">
                {heldEntries.map(([sym, p]) => (
                  <div className="position" key={sym}>
                    <span>
                      <SymLink sym={sym} /> <SidePill side={p.quantity > 0 ? "LONG" : "SHORT"} suffix={` ${Math.abs(p.quantity)}`} />
                      <br /><span className="muted">in at {num(p.avg_price)}, now {num(p.ltp)}</span>
                    </span>
                    <strong className={tone(p.unrealized_pnl)}>{money(p.unrealized_pnl)}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty">None open. At most 3 at a time, all closed by 15:15.</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
