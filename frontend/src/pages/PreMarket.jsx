import { useState } from "react";
import { Link } from "react-router-dom";
import { postJson, useAction, useApi } from "../api";
import LoadState from "../components/LoadState";
import { pct, tone } from "../format";
import { BiasPill } from "../components/Pill";
import { GuardNotes } from "../components/ListNotes";

const TABS = [
  ["watchlist", "Watchlist"], ["all", "All ranked"], ["avoid", "Avoid"],
];

function Row({ r, expanded, onToggle }) {
  return (
    <>
      <button type="button" className={`opp${expanded ? " expanded" : ""}`} aria-expanded={expanded} onClick={() => onToggle(r.symbol)}>
        <span className="opp-score" title="Pre-market score (daily data only)">{r.excluded ? "—" : r.score?.toFixed(0)}</span>
        <span>
          <span className="opp-name">
            {r.symbol} {r.excluded ? <span className="pill neutral">Avoid</span> : null}
            {r.status === "WATCHLIST" && <span className="pill solid">On today's list</span>}
          </span>
          <span className="opp-why">{r.excluded || (r.reasons || []).slice(0, 2).map((x) => x.text).join("; ")}</span>
        </span>
        <span className="opp-why">{r.name || ""}</span>
        <span className={`opp-chg ${tone(r.prev_chg_pct)}`}>{pct(r.prev_chg_pct)}</span>
      </button>
      {expanded && (
        <div className="opp-detail">
          <div className="rb-row" style={{ marginBottom: 10 }}>
            <div className="rb-chip"><b>Prior close</b><span>₹{r.close}</span></div>
            <div className="rb-chip"><b>Daily trend</b><span>{r.daily_trend}</span></div>
            <div className="rb-chip"><b>Daily ATR%</b><span>{r.atr_pct}%</span></div>
            <div className="rb-chip"><b>10-day RS vs NIFTY</b><span>{r.rs10 != null ? `${r.rs10}%` : "—"}</span></div>
            <div className="rb-chip"><b>From 52w high/low</b><span>{r.pct_from_high}% / {r.pct_from_low}%</span></div>
            <div className="rb-chip"><b>20d turnover</b><span>₹{r.turnover_cr} cr</span></div>
            <div className="rb-chip"><b>Long score</b><span>{r.long_score}</span></div>
            <div className="rb-chip"><b>Short score</b><span>{r.short_score}</span></div>
          </div>
          {r.event && <div className="tax" style={{ marginBottom: 10 }}>{r.event.purpose} on {r.event.date} — event risk.</div>}
          {r.catalyst && <div className="detail" style={{ marginBottom: 10 }}><b>Catalyst:</b> {r.catalyst}</div>}
          {!!(r.reasons || []).length && (
            <ul style={{ margin: "0 0 10px", paddingLeft: 18, fontSize: 13 }}>
              {r.reasons.map((x, i) => <li key={i}>{x.points >= 0 ? "+" : ""}{x.points} — {x.text}</li>)}
            </ul>
          )}
          <Link className="btn btn-link" to={`/stock/${encodeURIComponent(r.symbol)}`}>
            Open full page →
          </Link>
        </div>
      )}
    </>
  );
}

export default function PreMarket({ state: s }) {
  const [tab, setTab] = useState("watchlist");
  const [expanded, setExpanded] = useState(null);
  // A failed load is shown with a retry; it used to be swallowed, leaving the
  // ranking spinner up forever (#237).
  const { data, error, reload } = useApi("/api/premarket", 20000);
  const refreshAction = useAction(async () => {
    await postJson("/api/premarket/refresh");
    await new Promise((r) => setTimeout(r, 3000));
    reload();
  });
  const refreshing = refreshAction.busy;
  const refresh = refreshAction.run;

  if (!data) {
    return (
      <>
        <h2 className="h">Pre-market analysis</h2>
        <LoadState error={error} onRetry={reload} label="Loading the pre-market ranking…" />
      </>
    );
  }
  if (!data.result && data.running) {
    return (
      <>
        <h2 className="h">Pre-market analysis</h2>
        <p className="empty"><span className="spinner" aria-hidden="true" />Ranking the NIFTY 100 on last session's daily data — this takes under a minute…</p>
        {error && <LoadState error={error} onRetry={reload} />}
      </>
    );
  }
  if (data.error && !data.result) {
    return (
      <>
        <h2 className="h">Pre-market analysis</h2>
        <div className="tax" role="alert">{data.error}</div>
        <button className="btn" style={{ marginTop: 10 }} disabled={refreshing} onClick={refresh}>{refreshing ? "Trying again…" : "Try again"}</button>
        {refreshAction.error && <p className="down" role="alert">Couldn't start the refresh: {refreshAction.error}.</p>}
      </>
    );
  }
  const r = data.result;
  if (!r) return null;
  const m = r.market;
  const events = Object.entries(r.events_today || {});
  const exActions = Object.entries(r.ex_actions_today || {});

  // A design review found Overview's live picks and this page's shortlist can
  // visibly disagree with no explanation — read as a bug by a skimming user.
  // They're not a bug: one's live, one's last night's close. Say so.
  const livePicks = s?.scanner?.active;
  const picksDiffer = livePicks && livePicks.length > 0 &&
    JSON.stringify([...livePicks].sort()) !== JSON.stringify([...(r.watchlist || [])].sort());

  const groups = {
    watchlist: r.rows.filter((x) => x.status === "WATCHLIST"),
    all: r.rows.filter((x) => !x.excluded),
    avoid: r.rows.filter((x) => x.excluded),
  };
  const list = groups[tab];

  return (
    <>
      <h2 className="h">Pre-market analysis</h2>
      <p className="sub">
        {r.as_of_note}{" "}
        {r.selection?.mode === "liquidity"
          ? `${r.selection.rule} Scores below come from daily-chart facts (trend, relative strength, patterns) and are shown for reading, not used to choose the list.`
          : "Ranked purely on daily-chart facts (trend, relative strength, patterns)."}{" "}
        No invented gap or SGX-Nifty-style pre-open number, since this codebase doesn't have an honest source for one.
      </p>
      <GuardNotes guards={r.guards} />
      <button className="btn" disabled={refreshing || data.running} onClick={refresh} style={{ marginBottom: 16 }}>
        {(refreshing || data.running) && <span className="spinner" />}
        {refreshing || data.running ? "Refreshing…" : "Refresh"}
      </button>
      {refreshAction.error && <p className="down" role="alert" style={{ marginTop: -8 }}>Couldn't start the refresh: {refreshAction.error}.</p>}
      {error && <LoadState error={`the last update failed (${error}); showing the earlier ranking`} onRetry={reload} />}

      {picksDiffer && (
        <div className="tax" style={{ marginBottom: 16 }}>
          The live intraday scanner has since run and updated today's actual picks — this page still shows last
          night's pre-market read, which won't change again until tomorrow.{" "}
          <Link className="more" to="/intraday" style={{ padding: 0 }}>
            See today's list on Overview →
          </Link>
        </div>
      )}

      {!!(r.narrative || []).length && (
        <div className="cardbox" style={{ borderColor: "var(--book)" }}>
          <h2 className="h" style={{ fontSize: 16 }}>The morning take</h2>
          <p className="muted" style={{ margin: "0 0 10px", fontSize: 12.5 }}>
            Same facts as the cards below, read the way a trader talks through a pre-market note — not a new
            source of truth, and not a prediction.
          </p>
          {r.narrative.map((para, i) => (
            <p key={i} style={{ margin: i === r.narrative.length - 1 ? "10px 0 0" : "0 0 10px", fontSize: 13.5, lineHeight: 1.6 }}>
              {i === r.narrative.length - 1 ? <i>{para}</i> : para}
            </p>
          ))}
        </div>
      )}

      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>Last session's market read <BiasPill bias={m.bias} /></h2>
        <div className="rb-row" style={{ marginTop: 8 }}>
          <div className="rb-chip"><b>NIFTY close</b><span className={tone(m.nifty.chg_pct)}>{m.nifty.close} ({m.nifty.chg_pct > 0 ? "+" : ""}{m.nifty.chg_pct}%)</span></div>
          <div className="rb-chip"><b>NIFTY daily trend</b><span>{m.nifty.trend}</span></div>
          <div className="rb-chip"><b>India VIX</b><span className={m.vix_high ? "down" : ""}>{m.vix ?? "—"}</span></div>
          <div className="rb-chip"><b>Breadth</b><span>{m.breadth.adv} up / {m.breadth.dec} down ({m.breadth.pct_adv}%)</span></div>
        </div>
        <ul style={{ margin: "10px 0 0", paddingLeft: 18, fontSize: 13 }}>
          {m.reasons.map((x, i) => <li key={i}>{x}</li>)}
        </ul>
      </div>

      {(events.length > 0 || exActions.length > 0) && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>Today's event risk</h2>
          {events.length > 0 && (
            <div style={{ marginBottom: exActions.length ? 10 : 0 }}>
              <div className="detail" style={{ marginBottom: 4 }}>Results due (excluded from new trades):</div>
              <div className="rb-row">
                {events.map(([sym, ev]) => <div className="rb-chip" key={sym}><b>{sym}</b><span>{ev.purpose} — {ev.date}</span></div>)}
              </div>
            </div>
          )}
          {exActions.length > 0 && (
            <div>
              <div className="detail" style={{ marginBottom: 4 }}>Ex-date today (mechanical price gap, not a signal):</div>
              <div className="rb-row">
                {exActions.map(([sym, action]) => <div className="rb-chip" key={sym}><b>{sym}</b><span>{action}</span></div>)}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="tabs" style={{ marginTop: 16 }}>
        {TABS.map(([key, label]) => (
          <button key={key} className="tab" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>
            {label}<span className="n">{groups[key].length}</span>
          </button>
        ))}
      </div>
      <div>
        {list.length ? (
          list.map((row) => (
            <Row key={row.symbol} r={row} expanded={expanded === row.symbol} onToggle={(sym) => setExpanded((e) => (e === sym ? null : sym))} />
          ))
        ) : (
          <p className="empty">Nothing here right now.</p>
        )}
      </div>
    </>
  );
}
