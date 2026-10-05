import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { apiFetch, everyWhileVisible } from "../api";
import { clockIST, inr, money, tone } from "../format";
import { heldSymbols, scanRows, sessionInfo } from "../helpers";
import { describeKite } from "../kiteStatus";
import { useEngineControls } from "../useEngineControls";
import KiteConnectButton from "./KiteConnectButton";
import { disable as disableAlerts, enable as enableAlerts, enabled as alertsEnabled, supported as alertsSupported } from "../notifications";

// Grouped by what each page is for. The paper desk leads (README section
// 125), then the five paper books as peers, then the intraday engine's own
// pages, then research, then the Kite account. No book is "the strategy".
const NAV = [
  ["Paper desk", [["/", "Paper desk"], ["/process-log", "Process log"]]],
  ["Paper books", [["/intraday", "Intraday engine"], ["/jev-book", "Jev book"], ["/jev2-book", "Jev 2 book"],
    ["/rule-lab", "Rule lab"],
    ["/momentum-book", "Momentum book"]]],
  ["Intraday engine pages", [["/premarket", "Pre-market"], ["/day-plan", "Day plan"],
    ["/screener", "Screener", "picks"], ["/technical-analysis", "Technical analysis"], ["/trades", "Trades"],
    ["/journal", "Journal"]]],
  ["Research", [["/kronos", "Kronos"]]],
  ["Account", [["/portfolio", "Portfolio", "held"]]],
];

export function Sidebar({ state, liveLogOpen, onToggleLiveLog }) {
  const [alertsOn, setAlertsOn] = useState(alertsEnabled);

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
    let lastProbe = 0;
    // probe=true spends a real Kite API call to confirm the session. Worth it
    // on load and when the user comes back to the tab — both moments where a
    // stale answer is the one they'd act on — but not on the 15s poll, and at
    // most once a minute however often the window takes focus (#241).
    async function refresh(probe = false) {
      if (stopped) return;
      if (probe) lastProbe = Date.now();
      try {
        const res = await apiFetch(`/api/kite/status${probe ? "?probe=true" : ""}`, { timeoutMs: probe ? 20000 : undefined });
        if (!res.ok) return;
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
    refresh(false).then(() => { if (!stopped) refresh(true); });
    const onFocus = () => { if (Date.now() - lastProbe >= 60000) refresh(true); };
    window.addEventListener("focus", onFocus);
    const stopPolling = everyWhileVisible(() => refresh(false), 15000);
    return () => {
      stopped = true;
      window.removeEventListener("focus", onFocus);
      stopPolling();
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
  const controls = useEngineControls(state);
  const switching = controls.busy.live || controls.busy.paper;

  return (
    <header className={`statusbar${live ? " is-live" : ""}`}>
      <div className="session">
        <strong>{open ? "Market open" : "Market closed"}</strong>
        <span>{si ? si.label : ""}{state?.last_update_ts ? ` · updated ${clockIST(state.last_update_ts)}` : ""}</span>
      </div>
      <div className="stat"><small>Invested</small><strong>{inr(invested)}</strong></div>
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
        <KiteConnectButton className={`btn ${k.urgent ? "primary" : ""}`} title={k.detail} label={k.action} />
        {/* Live runs the same full warning as the Overview card's Go live (#234). */}
        <div className="segmented" role="group" aria-label="Trading mode" aria-busy={switching}>
          <button className="paper" aria-pressed={String(state?.paper_mode === true)} disabled={!state || switching}
            onClick={() => { if (state) controls.goPaper(); }}>
            {controls.busy.paper ? "Switching…" : "Paper"}
          </button>
          <button className="live" aria-pressed={String(state?.paper_mode === false)} disabled={!state || switching}
            onClick={() => { if (state?.paper_mode) controls.goLive(); }}>
            {controls.busy.live ? "Switching…" : "Live"}
          </button>
        </div>
      </div>
      <div className="session-bar"><div className="session-bar-fill" style={{ width: `${si ? si.pct : 0}%` }}></div></div>
    </header>
  );
}
