import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { pct, tone } from "../format";
import { analysisFor, heldSymbols, isReady, primaryRule, scanRows } from "../helpers";
import { SidePill } from "../components/Pill";
import { RuleTag } from "../components/RuleBook";
import RuleBook from "../components/RuleBook";

const TABS = [
  ["trading", "Trading"], ["watch", "Watching"], ["skipped", "Skipped"],
];
const SORT_OPTS = [["score", "Score"], ["chg_pct", "Change %"], ["symbol", "Symbol"]];

function sortRows(rows, sort) {
  if (!sort || !sort.key) return rows;
  const dir = sort.dir === "asc" ? 1 : -1;
  const val = (r) => (sort.key === "symbol" ? r.symbol : sort.key === "score" ? r.final_score : r[sort.key]);
  return [...rows].sort((a, b) => {
    const va = val(a), vb = val(b);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "string") return va.localeCompare(vb) * dir;
    return (va - vb) * dir;
  });
}

function OppRow({ s, r, held, expanded, onToggle }) {
  const navigate = useNavigate();
  const why = r.excluded || (r.reasons || []).slice(0, 2).map((x) => x.text).join("; ");
  const rule = primaryRule(r);
  const flag = held.has(r.symbol) ? <span className="pill solid">Holding</span> : isReady(s, r) ? <span className="pill solid">Ready</span> : null;
  const a = analysisFor(s, r.symbol);
  return (
    <>
      <div className={`opp${expanded ? " expanded" : ""}`} onClick={() => onToggle(r.symbol)}>
        <span className="opp-score" title="Scan score">{r.excluded ? "—" : r.final_score?.toFixed(0)}</span>
        <span>
          <span className="opp-name">
            {r.symbol} {r.excluded ? <span className="pill neutral">Skipped</span> : <SidePill side={r.side} />} {flag}
            <RuleTag text={rule} />
          </span>
          <div className="opp-why">{why}</div>
        </span>
        <span className="opp-why">{r.name || ""}</span>
        <span className={`opp-chg ${tone(r.chg_pct)}`}>{pct(r.chg_pct)}</span>
      </div>
      {expanded && (
        <div className="opp-detail">
          {<RuleBook r={r} b={a && a.b} />}
          <button className="btn" style={{ marginTop: 10 }} onClick={() => navigate(`/stock/${encodeURIComponent(r.symbol)}`)}>
            Open full page →
          </button>
        </div>
      )}
    </>
  );
}

export default function Screener({ state: s }) {
  const [tab, setTab] = useState("trading");
  const [sort, setSort] = useState(null);
  const [showAllWatch, setShowAllWatch] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const rows = scanRows(s);
  const held = useMemo(() => new Set(heldSymbols(s)), [s]);

  const groups = {
    trading: rows.filter((r) => r.status === "ACTIVE" || held.has(r.symbol)),
    watch: rows.filter((r) => r.status === "WATCH" && !held.has(r.symbol)),
    skipped: rows.filter((r) => r.excluded && !held.has(r.symbol)),
  };

  if (!rows.length) {
    return (
      <>
        <h2 className="h">Screener</h2>
        <p className="empty">The first scan is running. Ranked stocks appear here in about 30 seconds.</p>
      </>
    );
  }

  const list = groups[tab];
  const byLiquidity = s.scanner?.selection?.mode === "liquidity";
  const intro = {
    trading: byLiquidity
      ? `${s.scanner.selection.rule} Trader Sahab checks these for entries every 30 seconds.`
      : "Trader Sahab checks these for entries every 30 seconds.",
    watch: byLiquidity
      ? "Eligible stocks outside today's list. They are scored and shown, but not watched for entries."
      : "Ranked candidates that didn't make the active list.",
    skipped: "Filtered out today, with the reason.",
  }[tab];
  let shown = sortRows(list, sort);
  if (tab === "watch" && !showAllWatch) shown = shown.slice(0, 20);

  function toggleSort(key) {
    if (key === "clear") return setSort(null);
    setSort((prev) => (prev && prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "symbol" ? "asc" : "desc" }));
  }

  return (
    <>
      <h2 className="h">Screener</h2>
      <p className="sub">All 100 NIFTY stocks Trader Sahab ranks every scan. {intro} Click a row to expand its rule book inline.</p>
      <div className="tabs">
        {TABS.map(([key, label]) => (
          <button key={key} className="tab" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>
            {label}<span className="n">{groups[key].length}</span>
          </button>
        ))}
      </div>
      <div className="sortbar">
        Sort by{" "}
        {SORT_OPTS.map(([key, label]) => {
          const active = sort && sort.key === key;
          const arrow = active ? (sort.dir === "asc" ? "↑" : "↓") : "";
          return (
            <button key={key} className={`sortbtn${active ? " active" : ""}`} onClick={() => toggleSort(key)}>
              {label} {arrow}
            </button>
          );
        })}
        {sort && <button className="sortbtn" onClick={() => toggleSort("clear")}>Reset</button>}
      </div>
      <div>
        {shown.length ? (
          shown.map((r) => (
            <OppRow key={r.symbol} s={s} r={r} held={held} expanded={expanded === r.symbol} onToggle={(sym) => setExpanded((e) => (e === sym ? null : sym))} />
          ))
        ) : (
          <p className="empty">Nothing here right now.</p>
        )}
        {tab === "watch" && list.length > 20 && (
          <button className="more" onClick={() => setShowAllWatch((v) => !v)}>
            {showAllWatch ? "Show top 20" : `Show all ${list.length}`}
          </button>
        )}
      </div>
    </>
  );
}
