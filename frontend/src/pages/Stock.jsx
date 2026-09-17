import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api";
import { joinWords, num, pct, safeUrl, signed, tone } from "../format";
import { analysisFor, rowFor, scanRows, sentiment } from "../helpers";
import { SidePill } from "../components/Pill";
import RuleBook from "../components/RuleBook";
import Chart from "../components/Chart";
import SymLink from "../components/SymLink";
import Tip from "../components/Tip";
import ResearchDesk from "../components/ResearchDesk";

function PlanBox({ s, r, b, pos }) {
  const levels = [];
  if (b?.support) levels.push(<span key="s">Support <b>{num(b.support)}</b></span>);
  if (b?.resistance) levels.push(<span key="r">Resistance <b>{num(b.resistance)}</b></span>);
  if (b?.vwap) levels.push(<span key="v">VWAP <b>{num(b.vwap)}</b></span>);
  const lv = levels.length ? <div className="levels">{levels}</div> : null;

  if (pos && pos.quantity) {
    const long = pos.quantity > 0;
    return (
      <div className={`plan ${long ? "long" : "short"}`}>
        <h3>Holding {Math.abs(pos.quantity)} shares {long ? "long" : "short"}</h3>
        <p>
          Entered at {num(pos.avg_price)}, open P&amp;L <span className={tone(pos.unrealized_pnl)}>{signed(pos.unrealized_pnl, 0)}</span>.
          {pos.stop_price ? ` Stop ${num(pos.stop_price)}, target ${num(pos.target_price)}.` : ""} Closes at the stop, the target, an exit signal or 15:15.
        </p>
        {lv}
      </div>
    );
  }
  if (r && r.excluded) return <div className="plan"><h3>No trade in this stock today</h3><p>{r.excluded}</p></div>;
  const side = r ? r.side : b?.bias === "short" ? "SHORT" : "LONG";
  const verb = side === "SHORT" ? "short" : "buy";
  if (!b) return <div className="plan wait"><h3>Watching for a chance to {verb}</h3><p>A timing read appears once this stock ranks in the top 15 or is tracked.</p></div>;

  const m = s.market || {};
  const paused = (side === "LONG" && m.bias === "risk-off") || (side === "SHORT" && m.bias === "risk-on");
  const ready = side === "SHORT" ? b.short_ok : b.long_ok;
  const cl = b.checklist && b.checklist[side === "SHORT" ? "short" : "long"];
  if (ready && !paused && (!r || r.status === "ACTIVE")) {
    return (
      <div className={`plan ${side === "SHORT" ? "short" : "long"}`}>
        <h3>Ready to {verb}</h3>
        {cl && cl.stop != null ? (
          <p>Enter near {num(cl.entry)}, stop {num(cl.stop)}, target {num(cl.target)}, reward-to-risk {num(cl.rrr)} after costs, at {Math.round(cl.size_factor * 100)}% size.</p>
        ) : (
          <p>Every entry condition is met. The order goes in on the next check if risk limits allow.</p>
        )}
        {lv}
      </div>
    );
  }
  const waits = [];
  if (paused) waits.push(`New ${side === "LONG" ? "longs" : "shorts"} are paused while the market is ${m.bias === "risk-off" ? "weak" : "strong"}`);
  if (r && r.status !== "ACTIVE") waits.push("A place in the active list");
  (b.blockers || []).forEach((x) => waits.push(x));
  return (
    <div className="plan wait">
      <h3>Waiting to {verb}</h3>
      {waits.length ? <ul>{waits.map((w, i) => <li key={i}>{w}</li>)}</ul> : <p>Conditions are close. Waiting for the next candle.</p>}
      {lv}
    </div>
  );
}

function CaseBar({ title, value, thr, color, items, emptyText }) {
  const scale = thr * 1.6;
  const width = Math.max(0, Math.min(100, (value / scale) * 100));
  const mark = (thr / scale) * 100;
  return (
    <div className="case">
      <h4><span>{title}</span><span>{num(value, 1)} <span className="muted">of {thr}</span></span></h4>
      <div className="meter" role="img" aria-label={`${title}: ${num(value, 1)} of ${thr} needed`}>
        <i style={{ width: `${width}%`, background: color }}></i>
        <b style={{ left: `${mark}%` }}></b>
      </div>
      <ul className="evidence">
        {items.length ? items.map((x, i) => (
          <li key={i}><span className={`pts ${x.points < 0 ? "penalty" : ""}`}>{signed(x.points, 1)}</span><span>{x.text}</span></li>
        )) : <li><span></span><span className="muted">{emptyText}</span></li>}
      </ul>
    </div>
  );
}

function ChecklistView({ r, b }) {
  if (!b.checklist) return null;
  const side = r && r.side ? r.side.toLowerCase() : b.bias === "short" ? "short" : "long";
  const cl = b.checklist[side] || b.checklist.long;
  if (!cl) return null;
  const failing = cl.items.filter((i) => i.required && !i.ok).length;
  return (
    <>
      <h3 className="sub-title" style={{ marginTop: 0 }}>Zerodha Varsity checklist</h3>
      <p className="lede">
        {cl.passed ? `Every required point passes for a ${cl.side}.` : `${failing} required point${failing > 1 ? "s" : ""} fail${failing > 1 ? "" : "s"}, so there's no ${cl.side} trade.`}
        {cl.stop != null ? ` If taken: entry ${num(cl.entry)}, stop ${num(cl.stop)}, target ${num(cl.target)}, reward-to-risk ${num(cl.rrr)}.` : ""}
        {b.bar_time ? ` Based on the ${b.bar_time.slice(11, 16)} candle, the most recent one that has finished.` : ""}
        {" "}Every rule is checked in the open, and the exact source is next to it.
      </p>
      <ul className="checklist">
        {cl.items.map((i, idx) => {
          const state = i.ok ? "pass" : i.required ? "fail" : "soft";
          const mark = i.ok ? "✓" : i.required ? "✗" : "–";
          return (
            <li className={`check ${state}`} key={idx}>
              <span className="mark" aria-label={state}>{mark}</span>
              <span>
                {i.label}{!i.required && <span className="muted"> (sizes the trade)</span>}
                <br /><span className="muted">{i.detail}</span>
                <br /><span className="source">{i.source}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </>
  );
}

function TimingTab({ r, a }) {
  if (!a) return <p className="empty">No timing read yet. It runs on the scanner's top 15 and on every tracked stock while the market is open.</p>;
  const b = a.b;
  const patterns = (b.patterns || []).map((p) => p.name);
  return (
    <>
      {b.entry_mode === "checklist" && <ChecklistView r={r} b={b} />}
      {b.entry_mode === "checklist" && <h3 className="sub-title">Supporting evidence</h3>}
      <p className="lede">
        {a.live ? "Live read." : "From the last scan."} The stock is {b.regime} (<Tip k="adx">ADX</Tip> {num(b.adx, 0)}), its swing structure is {b.structure}, and the 15-minute trend is {b.htf_trend}.{" "}
        <Tip k="rsi">RSI</Tip> {num(b.rsi, 0)}{b.volume_ratio != null ? `, volume ${num(b.volume_ratio, 1)}× average` : ""}.
        {patterns.length ? ` Candle patterns: ${joinWords(patterns)}.` : ""}
      </p>
      <div className="cases">
        <CaseBar title="Case for buying" value={b.bull_score} thr={b.entry_threshold} color="var(--long)" items={b.reasons || []} emptyText="Nothing bullish yet." />
        <CaseBar title="Case for shorting" value={b.bear_score} thr={b.entry_threshold} color="var(--short)" items={b.bear_reasons || []} emptyText="Nothing bearish yet." />
      </div>
    </>
  );
}

function ScanTab({ r, totalRows }) {
  if (!r) return <p className="empty">This stock isn't in the latest scan. It's tracked because it's pinned or held.</p>;
  const cat = r.catalyst ? sentiment(r.catalyst.score) : null;
  return (
    <>
      <p className="lede">Ranked #{r.rank} of {totalRows}. As a long it scores {signed(r.long_score, 0)}, as a short {signed(r.short_score, 0)}; the stronger side is kept.</p>
      <ul className="evidence">
        {(r.reasons || []).length ? r.reasons.map((x, i) => (
          <li key={i}><span className={`pts ${x.points < 0 ? "penalty" : ""}`}>{signed(x.points, 0)}</span><span>{x.text}</span></li>
        )) : <li><span></span><span className="muted">No strong factors either way.</span></li>}
      </ul>
      {(r.swing_patterns || []).map((sw, i) => (
        <p className="note" key={i}>
          Confirmed <strong>{sw.name}</strong> on the daily chart ({sw.side}), Bulkowski's neckline/confirmation level {num(sw.level)}, structural stop {num(sw.stop)}.
          Source: Bulkowski, <em>Encyclopedia of Chart Patterns</em> — a daily-chart, US-stock statistic used here as a directional weight, not a guarantee for this market or timeframe.
        </p>
      ))}
      <dl className="facts-grid">
        <div><dt>Opening gap</dt><dd>{pct(r.gap_pct)}</dd></div>
        <div><dt>Versus NIFTY today</dt><dd><span className={tone(r.rs_today)}>{pct(r.rs_today)}</span></dd></div>
        <div><dt>Volume vs usual</dt><dd>{r.rvol == null ? "—" : `${num(r.rvol, 1)}×`}</dd></div>
        <div><dt>Daily range</dt><dd>{num(r.atr_pct, 1)}%</dd></div>
        <div><dt>Versus NIFTY, 10 days</dt><dd><span className={tone(r.rs10)}>{pct(r.rs10)}</span></dd></div>
        <div><dt>Daily trend</dt><dd>{r.daily_trend}</dd></div>
        <div><dt>Below 52-week high</dt><dd>{num(r.pct_from_high, 1)}%</dd></div>
        <div><dt>Above 52-week low</dt><dd>{num(r.pct_from_low, 1)}%</dd></div>
        <div><dt>Daily turnover</dt><dd>₹{num(r.turnover_cr, 0)} cr</dd></div>
        <div><dt>Beta vs NIFTY</dt><dd>{r.beta == null ? "—" : num(r.beta, 2)}</dd></div>
      </dl>
      {cat && <p className="note"><span className={cat.cls}>{cat.word} catalyst.</span> {r.catalyst.top}</p>}
    </>
  );
}

function NewsTab({ s, symbol, news }) {
  const cats = scanRows(s).filter((r) => r.catalyst).sort((a, b) => Math.abs(b.catalyst.score) - Math.abs(a.catalyst.score)).slice(0, 8);
  let body;
  if (!news) body = <p className="empty">Loading headlines…</p>;
  else if (news.error) body = <p className="empty">Couldn't load news ({news.error}). Retrying every minute.</p>;
  else {
    const overall = sentiment(news.score);
    const sources = Object.entries(news.sources || {}).filter(([, v]) => v).map(([k, v]) => `${v} from ${k}`);
    body = (
      <>
        <p className="lede">Overall tone is <span className={overall.cls}>{overall.word.toLowerCase()}</span> ({signed(news.score, 2)}) across {joinWords(sources) || "no sources"} in the last 72 hours.</p>
        {news.headlines.length ? (
          <ul className="feed">
            {news.headlines.map((h, i) => {
              const url = safeUrl(h.url);
              const t = sentiment(h.score);
              return (
                <li key={i}>
                  <div className="meta"><span><span className={t.cls}>{t.word}</span> {h.publisher || h.source}</span><span>{num(h.age_h, 0)}h ago</span></div>
                  <div className="body">{url ? <a href={url} target="_blank" rel="noopener noreferrer">{h.title}</a> : h.title}</div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="empty">No headlines name this company in the last 72 hours.</p>
        )}
      </>
    );
  }
  return (
    <>
      {body}
      <h3 className="sub-title">In the news across the NIFTY 100</h3>
      {cats.length ? (
        <ul className="feed">
          {cats.map((r) => {
            const t = sentiment(r.catalyst.score);
            return (
              <li key={r.symbol}>
                <div className="meta"><span><SymLink sym={r.symbol} /> <span className={t.cls}>{t.word}</span></span></div>
                <div className="detail">{r.catalyst.top}</div>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="empty">No notable filings or headlines yet today.</p>
      )}
    </>
  );
}

export default function Stock({ state: s }) {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState("timing");
  const [news, setNews] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setNews(null);
    (async () => {
      try {
        const res = await apiFetch(`/api/news/${encodeURIComponent(symbol)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) setNews(data);
      } catch (e) {
        if (!cancelled) setNews({ error: String(e.message || e), headlines: [] });
      }
    })();
    return () => { cancelled = true; };
  }, [symbol]);

  if (!symbol) return <p className="empty">Pick a stock from the Screener to see the agent's plan for it.</p>;

  const r = rowFor(s, symbol);
  const a = analysisFor(s, symbol);
  const pos = s.positions[symbol];
  const ltp = (s.indicators[symbol] && s.indicators[symbol].ltp) || (r && r.ltp);
  const b = a && a.b;

  const side = r && r.side ? r.side.toLowerCase() : b && b.bias === "short" ? "short" : "long";
  const cl = b && b.checklist ? b.checklist[side] || b.checklist.long : null;
  const plan = b ? { support: b.support, resistance: b.resistance, vwap: b.vwap, cl, side } : null;

  return (
    <>
      <button className="backlink" onClick={() => navigate("/screener")}>← Screener</button>
      <div className="stock-head">
        <div>
          <h1>{symbol} {r && !r.excluded && <SidePill side={r.side} suffix=" idea" />}</h1>
          <p>{r ? `${r.name}, ${r.industry}` : "Pinned or held stock"}</p>
        </div>
        <div className="price">
          {num(ltp)}
          {r && <small className={tone(r.chg_pct)}>{pct(r.chg_pct)} {s.market_status === "open" ? "today" : "last session"}</small>}
        </div>
      </div>
      <div id="stk-plan"><PlanBox s={s} r={r} b={b} pos={pos} /></div>
      <RuleBook r={r} b={b} />
      <Chart symbol={symbol} plan={plan} position={pos} patterns={b?.patterns} barTime={b?.bar_time} trades={s.trades} />
      <div className="chart-legend">
        <span><i style={{ background: "var(--focus)" }}></i><Tip k="ema20">EMA 20</Tip></span>
        <span><i style={{ background: "var(--book)" }}></i><Tip k="ema50">EMA 50</Tip></span>
        <span><i className="dash" style={{ borderColor: "var(--ink-2)" }}></i>Plan entry</span>
        <span><i className="dash" style={{ borderColor: "var(--short)" }}></i>Stop</span>
        <span><i className="dash" style={{ borderColor: "var(--long)" }}></i>Target</span>
        <span className="muted">— the checklist's trade plan if taken, not a price forecast</span>
      </div>
      <div className="tabs" role="tablist">
        <button className="tab" role="tab" aria-selected={tab === "timing"} onClick={() => setTab("timing")}>Timing read</button>
        <button className="tab" role="tab" aria-selected={tab === "scan"} onClick={() => setTab("scan")}>Why it ranks</button>
        <button className="tab" role="tab" aria-selected={tab === "news"} onClick={() => setTab("news")}>News{news && !news.error ? <span className="n">{news.count}</span> : null}</button>
        <button className="tab" role="tab" aria-selected={tab === "research"} onClick={() => setTab("research")}>Research desk</button>
      </div>
      <div className="tab-content">
        {tab === "timing" && <TimingTab r={r} a={a} />}
        {tab === "scan" && <ScanTab r={r} totalRows={scanRows(s).length || 100} />}
        {tab === "news" && <NewsTab s={s} symbol={symbol} news={news} />}
        {tab === "research" && <ResearchDesk symbol={symbol} watchlist={s.watchlist} />}
      </div>
    </>
  );
}
