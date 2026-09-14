import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch, apiJson } from "../api";
import { clock, dateLabel, money, num, pct, tone } from "../format";
import { analysisFor, heldSymbols, isReady, primaryRule, scanRows } from "../helpers";
import { RuleTag } from "../components/RuleBook";
import { SidePill } from "../components/Pill";
import SymLink from "../components/SymLink";
import Feed from "../components/Feed";
import { enabled as alertsEnabled, supported as alertsSupported } from "../notifications";

async function setMode(paperMode) {
  await apiFetch(`/api/mode`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper_mode: paperMode }),
  });
}

function AutonomyCard({ s }) {
  const [fno, setFno] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let stopped = false;
    apiJson("/api/fno/status").then((d) => !stopped && setFno(d)).catch(() => {});
    const id = setInterval(() => apiJson("/api/fno/status").then((d) => !stopped && setFno(d)).catch(() => {}), 20000);
    return () => { stopped = true; clearInterval(id); };
  }, []);

  const live = !s.paper_mode;
  const capital = s.risk_total_capital;

  async function goLive() {
    const msg =
      `This turns on real order placement — Trader Sahab will buy and sell on Zerodha automatically from now on, ` +
      `every ~30 seconds, on its own rules, with no per-trade confirmation from you or anyone else. It runs whether ` +
      `or not you're watching.\n\n` +
      `Real capital right now: ₹${capital?.toLocaleString("en-IN") ?? "—"} (synced from your Kite account).\n` +
      `F&O (options): ${fno?.enabled ? "ON" : "OFF"} — turn it on separately from Portfolio if you want option trades too.\n\n` +
      `Turn it back to Paper any time from this same control — that takes effect immediately, no confirmation needed.\n\n` +
      `Go live now?`;
    if (!confirm(msg)) return;
    setBusy(true);
    try { await setMode(false); } catch (e) {}
    setBusy(false);
  }

  async function goPaper() {
    setBusy(true);
    try { await setMode(true); } catch (e) {}
    setBusy(false);
  }

  return (
    <div className="cardbox" style={{ marginBottom: 20, borderColor: live ? "var(--short)" : undefined }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 className="h" style={{ fontSize: 16 }}>
            {live ? "Trading is live — running automatically" : "Autonomous trading is off (paper mode)"}
          </h2>
          <div className="detail" style={{ marginTop: 2 }}>
            {live
              ? "The engine is placing real orders on its own rules, unattended. No action needed from you."
              : "Simulated orders only. Flip this on and the engine takes it from there — no per-trade confirmation, ever, once it's live."}
          </div>
        </div>
        <button className={`btn ${live ? "" : "primary"}`} disabled={busy} onClick={live ? goPaper : goLive}>
          {busy ? "…" : live ? "Switch to Paper" : "Go live"}
        </button>
      </div>
      <div className="rb-row" style={{ marginTop: 12 }}>
        <div className="rb-chip"><b>Real capital</b><span>{money(capital)}</span></div>
        <div className="rb-chip"><b>F&amp;O (options)</b><span>{fno ? (fno.enabled ? "ON" : "OFF") : "…"}</span></div>
        <div className="rb-chip"><b>Alerts</b><span>{alertsSupported() ? (alertsEnabled() ? "ON" : "Off — enable in the header") : "Not supported in this browser"}</span></div>
      </div>
      {!live && capital != null && capital < 2000 && (
        <p className="muted" style={{ margin: "10px 0 0", fontSize: 12.5 }}>
          At ₹{capital.toLocaleString("en-IN")}, the 1% risk model sizes most stocks to 0 shares — going live at this
          capital likely places few or no cash-equity trades until the account is funded further.{" "}
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

export default function Overview({ state: s }) {
  const [scanning, setScanning] = useState(false);
  const [scanLabel, setScanLabel] = useState("Scan now");

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
      <AutonomyCard s={s} />
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

      <h2 className="h">Today's picks</h2>
      <p className="sub">The stocks Trader Sahab is actively watching for an entry, ranked by scan score. <a className="more" href="/screener">See the full ranked list →</a></p>
      {picks.length ? (
        <div className="grid3">{picks.map((r) => <PickCard key={r.symbol} s={s} r={r} held={held} />)}</div>
      ) : (
        <p className="empty">The scan hasn't found a stock that passes every filter yet.</p>
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
