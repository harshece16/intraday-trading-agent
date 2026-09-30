import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { apiFetch, explainRefusal, openKiteLogin, setTradingMode } from "../api";
import { clock, money, num, tone } from "../format";
import { heldSymbols, scanRows, sessionInfo } from "../helpers";
import { describeKite } from "../kiteStatus";
import { disable as disableAlerts, enable as enableAlerts, enabled as alertsEnabled, supported as alertsSupported } from "../notifications";

// Grouped by what each page is for. The momentum book is the strategy and
// leads (README section 116). The intraday engine's pages follow as its paper
// record, then the intraday research, then the Kite account.
const NAV = [
  ["The strategy", [["/", "Momentum book"]]],
  ["Intraday paper record", [["/intraday", "Overview"], ["/premarket", "Pre-market"], ["/day-plan", "Day plan"],
    ["/screener", "Screener", "picks"], ["/technical-analysis", "Technical analysis"], ["/trades", "Trades"],
    ["/journal", "Journal"]]],
  ["Intraday research", [["/jev-book", "Jev book"], ["/kronos", "Kronos"]]],
  ["Account", [["/portfolio", "Portfolio", "held"]]],
];

async function setMode(paperMode) {
  try {
    await setTradingMode(paperMode);
  } catch (e) {
    if (!explainRefusal(e)) alert(`Couldn't switch mode: ${e.message}`);
  }
}

export function Sidebar({ state, liveLogOpen, onToggleLiveLog }) {
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

  const counts = state ? {
    picks: scanRows(state).filter((r) => r.status === "ACTIVE").length,
    held: heldSymbols(state).length,
  } : {};
  const open = state?.market_status === "open";

  return (
    <aside className="sidebar">
      <Link to="/" className="brand">
        <span className={"dot" + (open ? " open" : "")} aria-hidden="true"></span>
        <b>Trader Sahab</b>
      </Link>
      <nav aria-label="Pages">
        {NAV.map(([group, links]) => (
          <div className="navgroup" key={group}>
            <div className="navgroup-label">{group}</div>
            {links.map(([path, label, count]) => (
              <NavLink key={path} to={path} end={path === "/"} className="navlink">
                {label}
                {count && counts[count] > 0 && <span className="n">{counts[count]}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">
        <button className={`sidebtn ${liveLogOpen ? "on" : ""}`} onClick={onToggleLiveLog} aria-pressed={liveLogOpen}
          title="Live terminal: every scan, setup, trade and alert, streamed as it happens">
          Live log
        </button>
        {alertsSupported() && (
          <button className={`sidebtn ${alertsOn ? "on" : ""}`} onClick={toggleAlerts} aria-pressed={alertsOn}
            title="Browser notifications for trade fills, risk warnings and price moves, while this tab is open">
            Browser alerts {alertsOn ? "on" : "off"}
          </button>
        )}
      </div>
    </aside>
  );
}

export default function StatusBar({ state }) {
  const [kite, setKite] = useState(null);

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
  const live = state && !state.paper_mode;

  return (
    <header className={`statusbar${live ? " is-live" : ""}`}>
      <div className="session">
        <strong>{open ? "Market open" : "Market closed"}</strong>
        <span>{si ? si.label : ""}{state?.last_update_ts ? ` · updated ${clock(state.last_update_ts)}` : ""}</span>
      </div>
      <div className="stat"><small>Invested</small><strong>₹{num(invested, 0)}</strong></div>
      <div className="stat" title="After brokerage, STT, exchange fees, GST and stamp duty">
        <small>Realized today</small>
        <strong className={tone(state?.realized_pnl_today)}>{money(state?.realized_pnl_today)}</strong>
      </div>
      <div className="stat"><small>Open P&amp;L</small><strong className={tone(state?.unrealized_pnl)}>{money(state?.unrealized_pnl)}</strong></div>
      <div className="statusbar-right">
        {state?.entries_paused && (
          <span className="kite-chip kite-chip--warn" title={`No new positions will open. Stops, targets and the ${state?.square_off_time || "15:08"} square-off still run. Resume from the intraday Overview.`}>
            <span className="dot" aria-hidden="true"></span>
            Entries paused
          </span>
        )}
        <span className={`kite-chip kite-chip--${k.tone}`} title={k.detail} aria-live="polite">
          <span className="dot" aria-hidden="true"></span>
          {k.label}
        </span>
        <button className={`btn ${k.urgent ? "primary" : ""}`} title={k.detail} onClick={openKiteLogin}>{k.action}</button>
        <div className="segmented" role="group" aria-label="Trading mode">
          <button className="paper" aria-pressed={String(state?.paper_mode === true)} onClick={() => setMode(true)}>Paper</button>
          <button className="live" aria-pressed={String(state?.paper_mode === false)} onClick={() => { if (confirm("Switch to live trading? Trader Sahab will place real orders on Zerodha.")) setMode(false); }}>Live</button>
        </div>
      </div>
      <div className="session-bar"><div className="session-bar-fill" style={{ width: `${si ? si.pct : 0}%` }}></div></div>
    </header>
  );
}
