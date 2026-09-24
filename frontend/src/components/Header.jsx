import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { apiFetch, explainRefusal, openKiteLogin, setTradingMode } from "../api";
import { clock, money, num, tone } from "../format";
import { sessionInfo } from "../helpers";
import { describeKite } from "../kiteStatus";
import { disable as disableAlerts, enable as enableAlerts, enabled as alertsEnabled, supported as alertsSupported } from "../notifications";

const PAGES = [
  ["/", "Overview"], ["/premarket", "Pre-Market"], ["/day-plan", "Day Plan"], ["/screener", "Screener"],
  ["/technical-analysis", "Technical Analysis"], ["/portfolio", "Portfolio"], ["/journal", "Journal"], ["/trades", "Trades"],
];

async function setMode(paperMode) {
  try {
    await setTradingMode(paperMode);
  } catch (e) {
    if (!explainRefusal(e)) alert(`Couldn't switch mode: ${e.message}`);
  }
}

export default function Header({ state, liveLogOpen, onToggleLiveLog }) {
  const navigate = useNavigate();
  const [kite, setKite] = useState(null);
  const [alertsOn, setAlertsOn] = useState(false);

  useEffect(() => { setAlertsOn(alertsEnabled()); }, []);

  async function toggleAlerts() {
    if (alertsOn) {
      disableAlerts();
      setAlertsOn(false);
      return;
    }
    const ok = await enableAlerts();
    setAlertsOn(ok);
    if (!ok) alert("Notifications are blocked for this site. Allow them in your browser's site settings to get trade and price alerts.");
  }

  useEffect(() => {
    let stopped = false;
    // probe=true spends a real Kite API call to confirm the session. Worth it
    // on load and when the user comes back to the tab — both moments where a
    // stale answer is the one they'd act on — but not on the 15s poll.
    async function refresh(probe = false) {
      try {
        const res = await apiFetch(`/api/kite/status${probe ? "?probe=true" : ""}`);
        const k = await res.json();
        if (!stopped) setKite(k);
      } catch (e) {
        /* backend not reachable yet */
      }
    }
    // Cheap answer first so the chip paints immediately, then the probe
    // refines it. Waiting on the probe left the header reading
    // "Checking Kite…" for as long as Kite took to answer — the one moment
    // the user is actually looking at it.
    refresh(false).then(() => refresh(true));
    const onFocus = () => refresh(true);
    window.addEventListener("focus", onFocus);
    const id = setInterval(() => refresh(false), 15000);
    return () => {
      stopped = true;
      window.removeEventListener("focus", onFocus);
      clearInterval(id);
    };
  }, []);

  const open = state?.market_status === "open";
  const si = state ? sessionInfo(state) : null;
  const invested = state
    ? Object.values(state.positions || {}).reduce((sum, p) => sum + (p.quantity ? Math.abs(p.quantity) * p.avg_price : 0), 0) +
      Object.values(state.fno_positions || {}).reduce((sum, p) => sum + (p.lots || 0) * (p.lot_size || 0) * (p.entry_premium || 0), 0)
    : 0;
  const k = describeKite(kite);

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => navigate("/")}>
          <span className={"dot" + (open ? " open" : "")}></span>
          <b>Trader Sahab</b>
          <span>{open ? "Market open" : "Market closed"}{state?.last_update_ts ? `, updated ${clock(state.last_update_ts)}` : ""}</span>
          <span className="countdown">{si ? `· ${si.label}` : ""}</span>
        </button>
        <div className="stat"><small>Invested</small><strong>₹{num(invested, 0)}</strong></div>
        <div className="stat" title="After brokerage, STT, exchange fees, GST and stamp duty">
          <small>Realized today</small>
          <strong className={tone(state?.realized_pnl_today)}>{money(state?.realized_pnl_today)}</strong>
        </div>
        <div className="stat"><small>Open P&amp;L</small><strong className={tone(state?.unrealized_pnl)}>{money(state?.unrealized_pnl)}</strong></div>
        <span className="divider"></span>
        <div className="kite">
          <span className={`kite-chip kite-chip--${k.tone}`} title={k.detail} aria-live="polite">
            <span className="dot" aria-hidden="true"></span>
            {k.label}
          </span>
          <button
            className={`btn ${k.urgent ? "primary" : ""}`}
            title={k.detail}
            onClick={openKiteLogin}
          >
            {k.action}
          </button>
        </div>
        {state?.entries_paused && (
          <span className="kite-chip kite-chip--warn" title="No new positions will open. Stops, targets and the 15:15 square-off still run. Resume from the Overview page.">
            <span className="dot" aria-hidden="true"></span>
            Entries paused
          </span>
        )}
        {alertsSupported() && (
          <button className={`btn ${alertsOn ? "primary" : ""}`} onClick={toggleAlerts} title="Browser notifications for trade fills, risk warnings, and price moves">
            {alertsOn ? "🔔 Alerts on" : "🔕 Enable alerts"}
          </button>
        )}
        <button className={`btn ${liveLogOpen ? "primary" : ""}`} onClick={onToggleLiveLog} title="Live terminal — every scan, setup, trade and alert, streamed as it happens">
          {liveLogOpen ? "▾ Live log" : "▸ Live log"}
        </button>
        <div className="segmented" role="group" aria-label="Trading mode">
          <button className="paper" aria-pressed={String(!!state?.paper_mode)} onClick={() => setMode(true)}>Paper</button>
          <button className="live" aria-pressed={String(!state?.paper_mode)} onClick={() => { if (confirm("Switch to live trading? Trader Sahab will place real orders on Zerodha.")) setMode(false); }}>Live</button>
        </div>
        <div className="session-bar"><div className="session-bar-fill" style={{ width: `${si ? si.pct : 0}%` }}></div></div>
      </header>
      <nav className="pagenav">
        {PAGES.map(([path, label]) => (
          <NavLink key={path} to={path} end={path === "/"} className="navlink">
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
