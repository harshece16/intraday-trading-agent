import { Link } from "react-router-dom";
import { useApi } from "../api";
import LoadState from "../components/LoadState";
import ProcessLines from "../components/ProcessLines";
import { money } from "../format";

const REPO = "https://github.com/harshece16/intraday-trading-agent/blob/main";

// Status → pill tone. Every book gets the same card and the same weight; the
// desk never calls one of them the strategy (README section 125).
const TONE = { running: "long", waiting: "neutral", skipped: "wait", off: "short", unknown: "short" };

function plural(n, word) {
  if (n === 1) return `${n} ${word}`;
  return `${n} ${word.endsWith("y") ? `${word.slice(0, -1)}ies` : `${word}s`}`;
}

function Today({ book }) {
  const t = book.today || {};
  if (book.id === "intraday") {
    return <>
      {plural(t.trades ?? 0, "closed trade")} · {money(t.net)}
      <small>{plural(t.entries ?? 0, "entry")} · {plural(t.open ?? 0, "open position")}{t.unrealized ? ` · open P&L ${money(t.unrealized)}` : ""}</small>
    </>;
  }
  if (book.id === "jev" || book.id === "jev2") {
    return <>
      {plural(t.trades ?? 0, "paper position")} · {t.scored ? money(t.net) : "—"}
      <small>{t.scored ? `${t.net_bp >= 0 ? "+" : "−"}${Math.abs(t.net_bp).toFixed(1)} bp a position after costs` : "nothing scored yet"} · {plural(t.skips ?? 0, "skip")}</small>
    </>;
  }
  if (book.id === "rule_lab") {
    return <>
      {plural(t.trades ?? 0, "closed trade")} · {t.trades ? money(t.net) : "—"}
      <small>{plural(t.opened ?? 0, "trade")} opened today · {t.open ?? 0} still open</small>
    </>;
  }
  return <>
    {plural(t.trades ?? 0, "trade")} · {t.trades ? money(t.net) : "—"}
    <small>{t.note || "the book is marked after the close; it trades only at a rebalance"}</small>
  </>;
}

function Record({ book }) {
  const r = book.record || {};
  const h = r.headline || {};
  const unit = book.id === "jev" || book.id === "jev2" ? "paper position" : book.id === "momentum" ? "delivery trade" : "closed trade";
  return <>
    {plural(r.trades ?? 0, unit)} · {r.net === null || r.net === undefined ? "—" : money(r.net)}
    <small>{h.label ? `${h.label}: ` : ""}<strong>{h.value}</strong>{h.note ? ` · ${h.note}` : ""}</small>
  </>;
}

function Card({ book }) {
  const s = book.status || {};
  return (
    <article className="desk-card" aria-labelledby={`desk-${book.id}`}>
      <header className="desk-head">
        <h3 id={`desk-${book.id}`}>{book.name}</h3>
        <span className={`pill ${TONE[s.state] || "neutral"}`}>{s.label}</span>
      </header>
      <p className="desk-about">{book.about}</p>
      {s.detail && <p className="desk-detail">{s.detail}</p>}
      <dl className="desk-facts">
        <div><dt>Today</dt><dd><Today book={book} /></dd></div>
        <div><dt>Record{book.record?.since ? ` since ${book.record.since}` : ""}</dt><dd><Record book={book} /></dd></div>
        <div><dt>{book.next?.label || "Next"}</dt><dd>{book.next?.text || "—"}</dd></div>
      </dl>
      <p className="desk-gate"><strong>Gate to go live:</strong> {book.gate}</p>
      <Link to={book.page} className="desk-link">Open the {book.name.toLowerCase()} page →</Link>
    </article>
  );
}

export default function PaperDesk() {
  const { data, error, reload } = useApi("/api/paper-desk", 30000);
  const log = useApi("/api/process-log?limit=12", 30000);
  if (!data) return <LoadState error={error} onRetry={reload} />;
  const items = log.data?.items || [];
  const total = log.data?.total ?? 0;

  return (
    <>
      <h2 className="h">Paper desk <span className="pill neutral" style={{ verticalAlign: "middle" }}>All paper</span></h2>
      <p className="sub">
        Five paper books run side by side as equal experiments. Each trades in paper and logs every process step and
        trade. <strong>None of them is the strategy</strong>: a book earns that only by passing the gate written down
        for it before its data was read, and nothing here moves real money. No intraday edge has been found
        (202 trials; looks L40 to L51), and the momentum book&apos;s backtest pass is narrow.{" "}
        <a href={`${REPO}/docs/research/decisions/decision-2026-10-05-paper-desk.md`} target="_blank" rel="noreferrer">Decision record</a>
        {" "}· <Link to="/process-log">Process log</Link>
      </p>

      <div className="desk-grid">
        {(data.books || []).map((b) => <Card key={b.id} book={b} />)}
      </div>

      <section className="mb-section">
        <div className="desk-strip-head">
          <h3>Process log — today</h3>
          <Link to="/process-log">{total ? `All ${total} lines →` : "Open →"}</Link>
        </div>
        <p className="lede muted" style={{ fontSize: 13 }}>
          The newest steps and trades from every book, in IST. Rule-lab trades are grouped by bar; the full list is
          on the process log page.
        </p>
        {log.error && !log.data ? <LoadState error={log.error} onRetry={log.reload} /> :
          <ProcessLines items={items} compact empty="Nothing recorded yet today." />}
      </section>

      <p className="muted" style={{ fontSize: 12, marginTop: 20 }}>
        As of {data.as_of ? data.as_of.replace("T", " ") : "—"} IST
        {data.session === false ? " · no NSE session today" : ""}. Read-only: these cards and the log are assembled
        from what the books already write; nothing on this page changes a book or places an order.
      </p>
    </>
  );
}
