import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../api";
import LoadState from "../components/LoadState";
import ProcessLines from "../components/ProcessLines";
import { BOOK_ORDER, BOOK_TEXT, kindLabel } from "../processLog";
import { istDay } from "../format";

// One unified log (README section 125): every process step and trade from all
// five paper books on one IST day, newest first, filterable by book and kind.
// Read-only: it only GETs /api/process-log while the tab is visible.
export default function ProcessLog() {
  const [params, setParams] = useSearchParams();
  const [today] = useState(() => istDay(Date.now() / 1000));   // the IST day when the page opened
  const day = params.get("day") || today;
  const book = params.get("book") || "";
  const kind = params.get("kind") || "";
  const query = useMemo(() => {
    const q = new URLSearchParams({ day, limit: "1000" });
    if (book) q.set("book", book);
    if (kind) q.set("kind", kind);
    return `/api/process-log?${q}`;
  }, [day, book, kind]);
  const { data, error, reload } = useApi(query, day === today ? 30000 : 0);

  function set(key, value) {
    const next = new URLSearchParams(params);
    if (value && !(key === "day" && value === today)) next.set(key, value); else next.delete(key);
    if (key === "book") next.delete("kind");          // a kind belongs to a book's vocabulary
    setParams(next, { replace: true });
  }

  const counts = data?.counts || {};
  const kinds = data?.kinds || [];

  return (
    <>
      <h2 className="h">Process log</h2>
      <p className="sub">
        Everything the five paper books did on one day, merged and newest first: the intraday engine&apos;s scans,
        setups, entries, exits, review cards and square-off; the Jev book&apos;s rounds and decisions; the rule
        lab&apos;s sessions and the trades it opened and closed (grouped by bar, each expandable); the momentum
        book&apos;s evening-job runs, trades, rebalances and alerts. Times are IST. Money is shown where there is
        money: realised P&amp;L on an exit, costs on a delivery trade, the rupee value of a Jev position&apos;s bp move
        on its ₹1 lakh notional. Read-only.
      </p>

      <form className="plog-filters" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
        <label>Day
          <input type="date" value={day} max={today} onChange={(e) => set("day", e.target.value)} />
        </label>
        <label>Book
          <select value={book} onChange={(e) => set("book", e.target.value)}>
            <option value="">All books</option>
            {BOOK_ORDER.map((b) => (
              <option key={b} value={b}>{BOOK_TEXT[b]}{counts[b] !== undefined ? ` (${counts[b]})` : ""}</option>
            ))}
          </select>
        </label>
        <label>Kind
          <select value={kind} onChange={(e) => set("kind", e.target.value)}>
            <option value="">All kinds</option>
            {kinds.map((k) => <option key={k} value={k}>{kindLabel(k)}</option>)}
          </select>
        </label>
        {(book || kind || day !== today) && (
          <button type="button" className="btn" onClick={() => setParams(new URLSearchParams(), { replace: true })}>Today, everything</button>
        )}
      </form>

      {!data ? <LoadState error={error} onRetry={reload} /> : (
        <>
          <p className="muted" style={{ fontSize: 13, margin: "10px 0" }}>
            {data.total} line{data.total === 1 ? "" : "s"} on {data.day}
            {book ? ` from the ${BOOK_TEXT[book] || book} book` : ""}{kind ? `, kind “${kindLabel(kind)}”` : ""}
            {data.truncated ? `; showing the newest ${data.items.length}` : ""}.
            {" "}Per book today: {BOOK_ORDER.map((b) => `${BOOK_TEXT[b]} ${counts[b] ?? 0}`).join(" · ")}.
          </p>
          <ProcessLines items={data.items} empty={`Nothing recorded on ${data.day}${book || kind ? " for this filter" : ""}.`} />
        </>
      )}
    </>
  );
}
