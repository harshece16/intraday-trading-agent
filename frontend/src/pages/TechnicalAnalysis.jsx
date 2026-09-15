import { useEffect, useState } from "react";
import { apiJson } from "../api";
import { BiasPill } from "../components/Pill";
import LlmSentimentPanel from "../components/LlmSentimentPanel";

function RuleChips({ rules }) {
  return (
    <div className="rb-row">
      {rules.map((r, i) => (
        <div className="rb-chip" title={r.source} key={i}><b>{r.key || r.name}</b><span>{r.source}</span></div>
      ))}
    </div>
  );
}

export default function TechnicalAnalysis() {
  const [m, setM] = useState(null);

  useEffect(() => {
    let cancelled = false;
    apiJson("/api/methods").then((data) => !cancelled && setM(data)).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  if (!m) return <p className="empty">Loading the method book…</p>;

  const noteCard = (section) =>
    section && (
      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>{section.title}</h2>
        <p className="muted" style={{ margin: "0 0 4px", fontSize: 13 }}>{section.source}</p>
        <p style={{ margin: 0, fontSize: 13 }}>{section.note}</p>
      </div>
    );

  const ruleSection = (section) =>
    section?.rules && (
      <div className="cardbox" style={{ marginTop: 16 }}>
        <h2 className="h" style={{ fontSize: 16 }}>{section.title}</h2>
        {section.note && <p style={{ margin: "0 0 10px", fontSize: 13 }}>{section.note}</p>}
        <RuleChips rules={section.rules} />
      </div>
    );

  return (
    <>
      <h2 className="h">Technical Analysis</h2>
      <p className="sub">Every technique Sahab's Dimaag actually trades on, with the book or paper behind it.</p>

      {m.checklist && (
        <div className="cardbox">
          <h2 className="h" style={{ fontSize: 16 }}>{m.checklist.title}</h2>
          <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>{m.checklist.intro}</p>
          <div className="rulebook-label">Checklist categories</div>
          <RuleChips rules={m.checklist.rules} />
        </div>
      )}

      {m.candlestick_patterns && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.candlestick_patterns.title}</h2>
          <p className="muted" style={{ margin: "0 0 4px", fontSize: 13 }}>{m.candlestick_patterns.source}</p>
          <p style={{ margin: "0 0 10px", fontSize: 13 }}>{m.candlestick_patterns.note}</p>
          <div className="rb-row">{m.candlestick_patterns.names.map((n) => <span className="pill neutral" key={n}>{n}</span>)}</div>
        </div>
      )}

      {m.daily_patterns?.patterns?.length > 0 && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.daily_patterns.title}</h2>
          <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>{m.daily_patterns.source} — {m.daily_patterns.note}</p>
          <div className="table-wrap">
            <table className="datatable">
              <thead><tr><th>Pattern</th><th>Bias</th><th>Rank</th><th>Bull fail%</th><th>Bull avg move</th><th>Bear fail%</th><th>Bear avg move</th></tr></thead>
              <tbody>
                {m.daily_patterns.patterns.map((p) => (
                  <tr key={p.name}>
                    <td>{p.name}</td><td><BiasPill bias={p.bias} /></td><td>{p.rank ?? "—"}</td>
                    <td>{p.bull_failure_rate_pct ?? "—"}%</td><td>{p.bull_avg_move_pct ?? "—"}%</td>
                    <td>{p.bear_failure_rate_pct ?? "—"}%</td><td>{p.bear_avg_move_pct ?? "—"}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {noteCard(m.reversal_days)}
      {noteCard(m.volume_confirmation)}

      {m.gaps && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.gaps.title}</h2>
          <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>{m.gaps.source} — {m.gaps.note}</p>
          <div className="rb-row">
            {Object.entries(m.gaps.close_within_week_pct || {}).map(([k, v]) => (
              <div className="rb-chip" key={k}><b>{k}</b><span>{v}% close within a week</span></div>
            ))}
          </div>
        </div>
      )}

      {ruleSection(m.trend)}
      {ruleSection(m.levels)}

      {m.momentum && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.momentum.title}</h2>
          <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>{m.momentum.source}</p>
          <div className="rb-row">{m.momentum.names.map((n) => <span className="pill neutral" key={n}>{n}</span>)}</div>
        </div>
      )}

      {m.news && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.news.title}</h2>
          <p style={{ margin: "0 0 10px", fontSize: 13 }}>{m.news.note}</p>
          <LlmSentimentPanel />
          <div className="table-wrap">
            <table className="datatable">
              <thead><tr><th>Source</th><th>Trust weight</th></tr></thead>
              <tbody>{m.news.sources.map((s) => <tr key={s.name}><td>{s.name}</td><td>{s.weight}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      )}

      {ruleSection(m.risk)}

      {m.seasonality && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.seasonality.title}</h2>
          <p style={{ margin: "0 0 10px", fontSize: 13 }}>{m.seasonality.note}</p>
          <RuleChips rules={m.seasonality.rules} />
        </div>
      )}

      {m.market_intelligence && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.market_intelligence.title}</h2>
          <p style={{ margin: "0 0 10px", fontSize: 13 }}>{m.market_intelligence.note}</p>
          <RuleChips rules={m.market_intelligence.rules} />
        </div>
      )}

      {m.fno && (
        <div className="cardbox" style={{ marginTop: 16 }}>
          <h2 className="h" style={{ fontSize: 16 }}>{m.fno.title}</h2>
          <p className="muted" style={{ margin: "0 0 4px", fontSize: 13 }}>{m.fno.source}</p>
          <p style={{ margin: "0 0 10px", fontSize: 13 }}>{m.fno.note}</p>
          <RuleChips rules={m.fno.rules} />
        </div>
      )}

      {m.not_yet_used && (
        <div className="tax" style={{ marginTop: 16 }}>
          <b>{m.not_yet_used.title}</b>
          <div style={{ marginTop: 8 }}>
            {m.not_yet_used.items.map((it, i) => (
              <div style={{ marginBottom: 8 }} key={i}><b>{it.name}</b><div className="detail">{it.reason}</div></div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
