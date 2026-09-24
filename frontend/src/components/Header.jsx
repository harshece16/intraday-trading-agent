import { useEffect, useRef, useState } from "react";
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

/* The top bar carries only what a trader needs at a glance on every page:
   is the market open, how is today going, which mode is this, and is Kite
   healthy. Everything else (Kite details and reconnect, invested amount,
   alerts, the live log, switching back to Paper) lives in the desk menu
   behind the mode button. Going LIVE is deliberately not in the header: it
   happens from Overview's trading control, which shows the full warning. */
export default function Header({ state, liveLogOpen, onToggleLiveLog }) {
  const navigate = useNavigate();
  const [kite, setKite] = useState(null);
  const [alertsOn, setAlertsOn] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

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
    // refines it.
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

  // Close the desk menu on an outside click or Escape.
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDown = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setMenuOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [menuOpen]);

  async function switchToPaper() {
    try {
      await setTradingMode(true);
    } catch (e) {
      if (!explainRefusal(e)) alert(`Couldn't switch to Paper: ${e.message}`);
    }
  }

  const open = state?.market_status === "open";
  const live = state ? !state.paper_mode : false;
  const si = state ? sessionInfo(state) : null;
  const invested = state
    ? Object.values(state.positions || {}).reduce((sum, p) => sum + (p.quantity ? Math.abs(p.quantity) * p.avg_price : 0), 0) +
      Object.values(state.fno_positions || {}).reduce((sum, p) => sum + (p.lots || 0) * (p.lot_size || 0) * (p.entry_premium || 0), 0)
    : 0;
  const k = describeKite(kite);
  const kiteNeedsEye = k.tone === "bad" || k.tone === "warn";

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => navigate("/")}
          title={state?.last_update_ts ? `Updated ${clock(state.last_update_ts)}` : undefined}>
          <span className={"dot" + (open ? " open" : "")}></span>
          <b>Trader Sahab</b>
          <span>{open ? "Market open" : "Market closed"}{si ? ` · ${si.label}` : ""}</span>
        </button>

        <div className="stat" title="After brokerage, STT, exchange fees, GST and stamp duty">
          <small>Realized today</small>
          <strong className={tone(state?.realized_pnl_today)}>{money(state?.realized_pnl_today)}</strong>
        </div>
        <div className="stat"><small>Open P&amp;L</small><strong className={tone(state?.unrealized_pnl)}>{money(state?.unrealized_pnl)}</strong></div>

        {/* Only states that need action earn a place in the bar; a healthy
            Kite session is shown by the dot on the desk button. */}
        {kiteNeedsEye && (
          <button className={`kite-chip kite-chip--${k.tone}`} title={k.detail} aria-live="polite" onClick={openKiteLogin}>
            <span className="dot" aria-hidden="true"></span>
            {k.label} · {k.action}
          </button>
        )}
        {state?.entries_paused && (
          <span className="kite-chip kite-chip--warn" title="No new positions will open. Stops, targets and the 15:15 square-off still run. Resume from the Overview page.">
            <span className="dot" aria-hidden="true"></span>
            Entries paused
          </span>
        )}

        <div className="desk" ref={menuRef}>
          <button
            className={`desk-btn${live ? " live" : ""}`}
            aria-haspopup="true"
            aria-expanded={menuOpen}
            aria-label={`${live ? "Live" : "Paper"} mode, ${k.label}. Open desk menu`}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span className={`dot kite-dot kite-dot--${k.tone}`} aria-hidden="true"></span>
            {live ? "Live" : "Paper"}
            <span className="caret" aria-hidden="true">▾</span>
          </button>
          {menuOpen && (
            <div className="desk-menu" role="menu">
              <div className="desk-row">
                <div>
                  <small>Mode</small>
                  <strong className={live ? "down" : ""}>{live ? "Live" : "Paper"}</strong>
                  <small>{live ? "Real orders on Zerodha" : "Simulated orders only"}</small>
                </div>
                {live ? (
                  <button className="btn" onClick={() => { setMenuOpen(false); switchToPaper(); }}>Switch to Paper</button>
                ) : (
                  <button className="btn" onClick={() => { setMenuOpen(false); navigate("/"); }} title="Going live happens from the trading control on Overview, which shows the full warning">Trading control</button>
                )}
              </div>
              <div className="desk-row">
                <div>
                  <small>Zerodha Kite</small>
                  <strong><span className={`kite-chip kite-chip--${k.tone}`} title={k.detail}><span className="dot" aria-hidden="true"></span>{k.label}</span></strong>
                </div>
                <button className={`btn ${k.urgent ? "primary" : ""}`} title={k.detail} onClick={openKiteLogin}>{k.action}</button>
              </div>
              <div className="desk-row">
                <div><small>Invested now</small><strong>₹{num(invested, 0)}</strong></div>
              </div>
              {alertsSupported() && (
                <div className="desk-row">
                  <div><small>Browser alerts</small><strong>{alertsOn ? "On" : "Off"}</strong></div>
                  <button className="btn" onClick={toggleAlerts} title="Browser notifications for trade fills, risk warnings, and price moves">
                    {alertsOn ? "Turn off" : "Turn on"}
                  </button>
                </div>
              )}
              <div className="desk-row">
                <div><small>Live log</small><strong>{liveLogOpen ? "Open" : "Closed"}</strong></div>
                <button className="btn" onClick={() => { setMenuOpen(false); onToggleLiveLog(); }}
                  title="Live terminal — every scan, setup, trade and alert, streamed as it happens">
                  {liveLogOpen ? "Close" : "Open"}
                </button>
              </div>
            </div>
          )}
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
