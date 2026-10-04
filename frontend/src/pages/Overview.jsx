import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { postJson } from "../api";
import { clockIST, dateLabel, money, num, pct, tone } from "../format";
import { analysisFor, checklistSide, heldSymbols, isReady, primaryRule, scanRows } from "../helpers";
import { RuleTag } from "../components/RuleBook";
import { SidePill } from "../components/Pill";
import SymLink from "../components/SymLink";
import Feed from "../components/Feed";
import Chart from "../components/Chart";
import ReviewQueue from "../components/ReviewQueue";
import AutonomyCard from "../components/AutonomyCard";
import KiteConnectButton from "../components/KiteConnectButton";
import { feedText, fixedText } from "../components/ListNotes";


const ONBOARD_KEY = "sahab_onboarding_dismissed";

function OnboardingBanner({ s }) {
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

  return (
    <div className="cardbox" style={{ marginBottom: 20, borderColor: "var(--wait)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 className="h" style={{ fontSize: 16 }}>First time here? Three things before you start</h2>
          <ol style={{ margin: "8px 0 0", paddingLeft: 20, fontSize: 13.5, lineHeight: 1.9 }}>
            <li><b>Connect Kite</b>: click Connect Kite in the top bar. Live prices, your holdings and real orders need it. Without it, paper trading uses delayed prices.</li>
            <li><b>Confirm you're in Paper mode</b> — check the Paper/Live switch in the bar at the top. Paper is the safe default and simulates everything; Live places real orders.</li>
            <li><b>Read the Dimaag Scorecard on the Journal page</b> before ever considering Live — it shows, honestly, whether this system has actually proven a real edge yet.</li>
          </ol>
        </div>
        <button className="btn" onClick={dismiss}>Dismiss</button>
      </div>
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
        <KiteConnectButton className="btn primary" label={stalled ? "Try again" : "Reconnect"} />
      </div>
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
  const tracked = (sc && sc.active) || [];
  const held = heldSymbols(s).length;
  const sentences = [
    `NIFTY ${n.chg_pct >= 0 ? "rose" : "fell"} ${Math.abs(n.chg_pct).toFixed(2)}% ${closed ? `on ${dateLabel(m.session_date)}` : "today"} and ${m.breadth.dec} of ${m.breadth.adv + m.breadth.dec} stocks fell.`,
    tracked.length ? `Tracking ${tracked.length} stocks; the checklist picks the side on each.` : "No stock passes every filter yet.",
    held ? `${held} open position${held > 1 ? "s" : ""}.` : "No open positions.",
  ];
  if (m.vix_high) sentences.push(`India VIX is high, so new positions are half size.`);
  if (closed) sentences.push("Trading resumes at 9:15.");
  return { lead, rest: sentences.join(" ") };
}

function PickCard({ s, r, held }) {
  const ready = isReady(s, r);
  const why = (r.reasons || []).slice(0, 2).map((x) => x.text).join("; ");
  const rule = primaryRule(r);
  return (
    <Link className="pickcard" to={`/stock/${encodeURIComponent(r.symbol)}`}>
      <div className="row1">
        <span className="sym">{r.symbol}</span>
        {r.long_only ? <span className="pill neutral" title="This stock has a fixed price band, so it is never shorted">Long only</span> : null}
        {held.has(r.symbol) ? <span className="pill solid">Holding</span> : ready ? <span className="pill solid">Ready</span> : null}
      </div>
      <div className="why">{why}</div>
      <RuleTag text={rule} />
      <div className="row2"><span>Score {num(r.final_score, 0)}</span><span className={tone(r.chg_pct)}>{pct(r.chg_pct)}</span></div>
    </Link>
  );
}

function MiniChartCard({ s, r, held }) {
  const a = analysisFor(s, r.symbol);
  const b = a && a.b;
  const pos = s.positions[r.symbol];
  const side = checklistSide(r, b);
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
    <div className="cardbox mini-chart-card">
      <div className="mini-chart-head">
        <Link className="sym mini-chart-link" to={`/stock/${encodeURIComponent(r.symbol)}`}>{r.symbol}</Link>
        <span style={{ display: "flex", gap: 6 }}>
          {held.has(r.symbol) ? <span className="pill solid">Holding</span> : null}
          {b ? <SidePill side={side.toUpperCase()} suffix=" plan" /> : null}
        </span>
      </div>
      <Chart symbol={r.symbol} plan={plan} position={pos} patterns={b?.patterns} barTime={b?.bar_time} trades={s.trades} className="mini-chart" compact />
      <div className="mini-chart-plan">{planLine}</div>
      <Link className="more" to={`/stock/${encodeURIComponent(r.symbol)}`}>Open {r.symbol} →</Link>
    </div>
  );
}

export default function Overview({ state: s }) {
  const [scanning, setScanning] = useState(false);
  const [scanLabel, setScanLabel] = useState("Scan now");

  async function triggerScan() {
    setScanning(true);
    setScanLabel("Scanning…");
    try {
      const data = await postJson("/api/scan");
      setScanLabel(data.started ? "Scan started" : "Already scanning");
    } catch (e) {
      setScanLabel(`Couldn't scan: ${e.message}`);
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
      <KiteSessionAlert s={s} />
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
            <small>{sc ? `Scanned ${sc.scanned} stocks at ${clockIST(sc.ts)}` : ""}</small>
          </div>
        </div>
      </section>

      <AutonomyCard s={s} />
      <ReviewQueue s={s} />

      <h2 className="h" style={{ marginTop: 40 }}>Today's list</h2>
      <p className="sub">
        {sc?.selection?.mode === "liquidity"
          ? `Today's list is the most-traded eligible stocks, chosen once and kept all day. ${fixedText(sc.selection)} It is chosen for low trading cost, not as a prediction. Cards are ordered by scan score. ${feedText(sc.feed)} `
          : "The stocks Trader Sahab is actively watching for an entry, ranked by scan score. "}
        <Link className="more" to="/screener">See the full list →</Link>
      </p>
      {picks.length ? (
        <div className="grid3">{picks.map((r) => <PickCard key={r.symbol} s={s} r={r} held={held} />)}</div>
      ) : (
        <p className="empty">The scan hasn't found a stock that passes every filter yet.</p>
      )}

      <div className="section-gap grid2">
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
              <p className="empty">None open. At most 3 at a time, all closed by {s.square_off_time || "15:08"}.</p>
            )}
          </div>
        </div>
        <div>
          <h2 className="h">What Trader Sahab is doing</h2>
          <p className="sub">The last few scans, picks and trades.</p>
          <Feed items={(s.activity || []).slice(0, 6)} />
        </div>
      </div>

      {picks.length > 0 && (
        <div className="section-gap">
          <h2 className="h">Live charts</h2>
          <p className="sub">
            Real candles, EMA 20/50 and the checklist's current plan for each pick — the entry, stop and target lines are
            the same numbers a real order would use, never a projected price path. Open a stock for its full page.
          </p>
          <div className="mini-chart-grid">
            {picks.map((r) => <MiniChartCard key={r.symbol} s={s} r={r} held={held} />)}
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Latest session shown. Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView</a>.
          </p>
        </div>
      )}
    </>
  );
}
