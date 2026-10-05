import { money } from "../format";
import SymLink from "./SymLink";
import { BOOK_TEXT, kindLabel } from "../processLog";

function Details({ d, kind }) {
  if (!d || !d.length) return null;
  const closed = kind === "lab_exit";
  return (
    <details className="plog-details">
      <summary>{d.length} trade{d.length === 1 ? "" : "s"}</summary>
      <div className="table-wrap">
        <table className="datatable plog-table">
          <thead>
            <tr>
              <th>Rule</th><th>Stock</th><th>Side</th><th>Qty</th><th>{closed ? "Exit" : "Entry"}</th>
              {closed ? <><th>Why</th><th className="num">Net bp</th><th className="num">Net ₹</th></> : <th>Signal bar</th>}
            </tr>
          </thead>
          <tbody>
            {d.map((t, i) => (
              <tr key={`${t.rule}-${t.symbol}-${i}`}>
                <td><strong>{t.rule}</strong></td>
                <td><SymLink sym={t.symbol} /></td>
                <td className={t.side === "LONG" ? "up" : "down"}>{t.side === "LONG" ? "Long" : "Short"}</td>
                <td>{t.qty ?? "—"}</td>
                <td>{t.price != null ? Number(t.price).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"}</td>
                {closed
                  ? <><td className="muted">{t.reason || "—"}</td>
                    <td className={`num ${t.net_bp > 0 ? "up" : t.net_bp < 0 ? "down" : ""}`}>{t.net_bp != null ? `${t.net_bp >= 0 ? "+" : "−"}${Math.abs(t.net_bp).toFixed(1)}` : "—"}</td>
                    <td className={`num ${t.net_rs > 0 ? "up" : t.net_rs < 0 ? "down" : ""}`}>{money(t.net_rs)}</td></>
                  : <td className="muted">{t.signal || "—"}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

/** One line per process step or trade, newest first, tagged by book, kind,
 *  IST time and symbol, with money where there is money. Read-only. */
export default function ProcessLines({ items, compact = false, empty = "Nothing recorded for this day." }) {
  if (!items || !items.length) return <p className="empty">{empty}</p>;
  return (
    <ol className={`plog${compact ? " compact" : ""}`} aria-label="Process log">
      {items.map((a, i) => (
        <li key={`${a.ts}-${a.book}-${a.kind}-${i}`} className={`plog-line level-${a.level || "info"}`}>
          <time className="plog-time" dateTime={new Date(a.ts * 1000).toISOString()}>{compact ? a.time.slice(0, 5) : a.time}</time>
          <span className="plog-tags">
            <span className={`book-tag book-${a.book}`}>{BOOK_TEXT[a.book] || a.book}</span>
            <span className={`plog-kind kind ${a.kind}`}>{kindLabel(a.kind)}</span>
          </span>
          <span className="plog-body">
            {a.symbol && <><SymLink sym={a.symbol} /> </>}
            {a.message}
            {!compact && <Details d={a.details} kind={a.kind} />}
          </span>
          <span className={`plog-money ${a.money > 0 ? "up" : a.money < 0 ? "down" : "muted"}`}>
            {a.money === null || a.money === undefined ? "" : money(a.money)}
          </span>
        </li>
      ))}
    </ol>
  );
}
