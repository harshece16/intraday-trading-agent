import { Link } from "react-router-dom";
import { useApi } from "../api";
import LoadState from "../components/LoadState";
import { money, num, tone } from "../format";
import SymLink from "../components/SymLink";

const REPO = "https://github.com/harshece16/intraday-trading-agent/blob/main";

const STATUS = {
  not_started: ["neutral", "Not started", "The first evening job hasn't run yet. It runs after 19:30 on trading days."],
  waiting_for_month_end: ["wait", "Waiting for its first rebalance", "The book buys its first 15 names at the close of the first session of a month."],
  active: ["long", "Active (paper)", "Holding 15 names; rebalanced on the first session of each month."],
  switched_off: ["short", "Switched off", "The book fell below its pre-registered band and stopped itself."],
};

const WHY = { locked: "Locked at its price band", no_trade: "Did not trade" };
const SIDE = { BUY: ["up", "Bought"], SELL: ["down", "Sold"], "CANCELLED BUY": ["muted", "Buy cancelled"] };

// What the trade row should say beyond its figures: it waited, it was sold in
// trade-for-trade, or it was given up after five sessions.
function tradeNote(t) {
  const notes = [];
  if (t.side === "CANCELLED BUY") notes.push(`No fill in five sessions since ${t.ordered}`);
  else if (t.ordered) notes.push(`Waited since ${t.ordered}`);
  if (t.series) notes.push(`In trade-for-trade (${t.series})`);
  return notes.join(" · ") || "—";
}

function pctOf(x, d = 2) {
  return x === null || x === undefined ? "—" : `${x >= 0 ? "+" : "−"}${Math.abs(x * 100).toFixed(d)}%`;
}

function plain(x) {
  return `${(x * 100).toFixed(2)}%`;
}

function day(iso) {
  return iso ? new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—";
}

function monthName(iso) {
  return new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

function NavChart({ nav }) {
  if (!nav || nav.length < 2) return <p className="empty">The value chart starts the session after the first rebalance.</p>;
  const b0 = nav[0].book, m0 = nav[0].bench;
  const book = nav.map((r) => (r.book / b0) * 100);
  const bench = nav.map((r) => (r.bench / m0) * 100);
  const lo = Math.min(...book, ...bench), hi = Math.max(...book, ...bench);
  const w = 640, h = 180, pad = 6;
  const x = (i) => pad + (i / (nav.length - 1)) * (w - 2 * pad);
  const y = (v) => h - pad - ((v - lo) / (hi - lo || 1)) * (h - 2 * pad);
  const path = (s) => s.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <figure style={{ margin: "8px 0 0" }}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Book value against its benchmark, both starting at 100">
        <path d={path(bench)} fill="none" stroke="var(--ink-2)" strokeWidth="1.5" strokeDasharray="4 3" />
        <path d={path(book)} fill="none" stroke="var(--long)" strokeWidth="2" />
      </svg>
      <figcaption className="muted" style={{ fontSize: 12 }}>
        Solid: the book. Dashed: its benchmark, the same 200 stocks equal-weighted. Both start at 100 on {nav[0].date}.
      </figcaption>
    </figure>
  );
}

// One row per completed month: the book against its benchmark, and the band's
// own running figure. Before the first month completes it says so, rather
// than showing zeros as if they were results.
function MonthlyReport({ data }) {
  const months = data.months || [];
  const band = data.band || {};
  const opening = data.opening_rebalance;
  if (!months.length) {
    const firstClose = data.first_rebalance ? data.next_rebalance : null;
    return (
      <p className="note" role="status">
        <strong>No month has completed yet, so there is no result to report.</strong>{" "}
        {opening
          ? <>The book bought its first {opening.bought} stocks at the {day(opening.date)} close. Its first month ends at the
              rebalance at the {day(firstClose)} close, and the first row appears after that evening's job.</>
          : <>The book has not traded yet. It buys its first 15 stocks at the {day(data.next_rebalance)} close; the first
              month ends at the rebalance a month later.</>}
      </p>
    );
  }
  return (
    <>
      <div className="table-wrap">
        <table className="datatable">
          <thead>
            <tr>
              <th>Month</th><th className="num">Book</th><th className="num">Benchmark</th><th className="num">Excess</th>
              <th className="num">Cumulative excess</th><th className="num">Band floor</th>
              <th className="num">Turnover</th><th className="num">Costs</th>
            </tr>
          </thead>
          <tbody>
            {[...months].reverse().map((m) => {
              const floor = m.n >= band.from_month
                ? m.n * band.expected_monthly_excess - 2 * band.monthly_excess_sd * Math.sqrt(m.n) : null;
              return (
                <tr key={m.start}>
                  <td>
                    <strong>{monthName(m.start)}</strong>
                    <div className="muted" style={{ fontSize: 12 }}>{day(m.start)} to {day(m.end)} · month {m.n}</div>
                  </td>
                  <td className={`num ${tone(m.book_return)}`}>{pctOf(m.book_return)}</td>
                  <td className={`num ${tone(m.bench_return)}`}>{pctOf(m.bench_return)}</td>
                  <td className={`num ${tone(m.excess)}`}><strong>{pctOf(m.excess)}</strong></td>
                  <td className={`num ${tone(m.cumulative_excess)}`}>{pctOf(m.cumulative_excess)}</td>
                  <td className="num muted">{floor === null ? "not yet" : pctOf(floor, 1)}</td>
                  <td className="num">{m.turnover === null ? "—" : `${(m.turnover * 100).toFixed(1)}%`}</td>
                  <td className="num">₹{num(m.costs, 0)}<div className="muted" style={{ fontSize: 12 }}>{m.bought} in, {m.sold} out</div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
        A month runs from one rebalance close to the next. Returns are after every charge and 0.05% slippage a side,
        including the rebalance that closes the month. Excess is the book's return minus the benchmark's; the
        cumulative excess adds the months up, as the band does. Turnover is (bought + sold) ÷ 2 ÷ the book's value
        at the start of the month.
        {opening ? ` The opening rebalance on ${day(opening.date)} bought ${opening.bought} stocks for ₹${num(opening.costs, 0)} of charges and slippage, before the first month.` : ""}
      </p>
    </>
  );
}

function Band({ data }) {
  const b = data.band;
  if (!b) return null;
  const says = {
    not_active: `Not applied yet: the band starts at month ${b.from_month}. ${b.months ? `${b.months} month${b.months === 1 ? "" : "s"} counted so far.` : "No month counted yet."}`,
    inside: `Inside the band, ${((b.cumulative_excess - b.floor) * 100).toFixed(2)} percentage points above the floor.`,
    below: "Below the floor.",
    switched_off: "The book fell below its floor and switched itself off. Nothing turns it back on.",
  }[b.state];
  return (
    <section className="mb-section">
      <h3>Switch-off band</h3>
      <p className="lede muted" style={{ fontSize: 14 }}>
        Fixed before the first rebalance (the pre-registration's notes on the forward paper book): after n months the
        book is switched off if its cumulative excess falls below n × {plain(b.expected_monthly_excess)} − 2 ×{" "}
        {plain(b.monthly_excess_sd)} × √n, from month {b.from_month}. That floor is {pctOf(b.floor_at_start, 1)} at month{" "}
        {b.from_month}. The figures are trial 126's backtest.
      </p>
      <dl className="band-row">
        <div><dt>Months counted</dt><dd>{b.months}</dd></div>
        <div><dt>Expected so far</dt><dd>{b.months ? pctOf(b.expected_cumulative) : "—"}</dd></div>
        <div><dt>Cumulative excess</dt><dd className={tone(b.cumulative_excess)}>{pctOf(b.cumulative_excess)}</dd></div>
        <div><dt>Floor now</dt><dd>{b.active ? pctOf(b.floor) : `from month ${b.from_month}`}</dd></div>
      </dl>
      <p className={b.state === "below" || b.state === "switched_off" ? "down" : "muted"} style={{ fontSize: 14, margin: "10px 0 0" }}>{says}</p>
    </section>
  );
}

export default function MomentumBook() {
  const { data, error, reload } = useApi("/api/momentum-book", 60000);
  if (!data) return <LoadState error={error} onRetry={reload} />;

  const [pillClass, label, blurb] = STATUS[data.status] || ["neutral", data.status, ""];
  const excess = data.cumulative_excess;
  const checks = data.data || {};           // the evening job's data checks (#159)
  const since = data.since_start || {};

  return (
    <>
      <h2 className="h">Momentum book <span className={`pill ${pillClass}`} style={{ verticalAlign: "middle" }}>{label}</span></h2>
      <p className="sub">
        Trader Sahab&apos;s strategy: hold the 15 of NSE&apos;s 200 most-traded stocks with the strongest 6- and
        12-month momentum, in delivery, rebalanced monthly. It is the one strategy that passed its pre-registered test
        (trial 120) and, narrowly, its re-run on repaired prices (trial 126: +0.71% a month over its benchmark in the
        backtest). <strong>Paper only</strong>, with ₹10 lakh:
        no order is placed. Real money comes only after months of paper results agree with the backtest, and it is
        not a guarantee: momentum has losing years (−12% against its benchmark in 2025).{" "}
        <a href={`${REPO}/docs/research/decisions/decision-2026-09-30-momentum-core.md`} target="_blank" rel="noreferrer">Decision record</a>
        {" "}· the intraday engine runs as a <Link to="/intraday">paper record</Link>.
      </p>
      <p className="muted" style={{ marginTop: -8 }}>{data.status_reason || data.note || blurb}</p>
      {checks.problem && (
        <p className="down" role="alert" style={{ fontSize: 13 }}>
          The last evening run stopped early: {checks.problem}. Nothing past that day is traded or marked until the
          data is in.
        </p>
      )}

      <div className="mb-facts">
        <div className="mb-fact"><small>Book value</small><strong>₹{num(data.book_value, 0)}</strong>
          <span className={tone(since.book)}>{pctOf(since.book)} since the start</span></div>
        <div className="mb-fact"><small>Benchmark value</small><strong>₹{num(data.bench_value, 0)}</strong>
          <span className={tone(since.bench)}>{pctOf(since.bench)} · the same 200 stocks, equal-weighted</span></div>
        <div className="mb-fact"><small>Cumulative excess</small>
          <strong className={tone(excess)}>{data.excess_months ? pctOf(excess) : "—"}</strong>
          <span>{data.excess_months ? `over ${data.excess_months} month${data.excess_months === 1 ? "" : "s"}` : "no month complete yet"}</span></div>
        <div className="mb-fact"><small>Next rebalance</small><strong>{day(data.next_rebalance)}</strong>
          <span>{data.status === "switched_off" ? "none: the book is off" : "at the close; the job runs after 19:30"}
            {data.next_rebalance_calendar_ok === false ? " (no NSE holiday list for that year yet)" : ""}</span></div>
      </div>

      <section className="mb-section">
        <h3>Month by month against the benchmark</h3>
        <p className="lede muted" style={{ fontSize: 14 }}>
          The benchmark is the pre-registered one, the equal-weighted 200: the same 200 most-traded NSE stocks the
          book ranks, equal-weighted, paying the same percentage costs. It is not a NIFTY index.
        </p>
        {data.month_to_date && data.status !== "switched_off" && (
          <p style={{ fontSize: 14, margin: "0 0 12px" }}>
            <strong>{monthName(data.month_to_date.start)} so far</strong>, from the {day(data.month_to_date.start)} rebalance
            to the {day(data.month_to_date.to)} close: book <span className={tone(data.month_to_date.book)}>{pctOf(data.month_to_date.book)}</span>,
            benchmark <span className={tone(data.month_to_date.bench)}>{pctOf(data.month_to_date.bench)}</span>. Not counted
            until the month completes at the next rebalance.
          </p>
        )}
        <MonthlyReport data={data} />
      </section>

      <Band data={data} />

      <section className="mb-section">
        <h3>Value against the benchmark</h3>
        <NavChart nav={data.nav} />
      </section>

      <section className="mb-section">
        <h3>What the book holds now</h3>
        {data.holdings && data.holdings.length ? (
          <div className="table-wrap">
            <table className="datatable">
              <thead><tr><th>Stock</th><th>Held since</th><th>Invested</th><th>Fill price</th></tr></thead>
              <tbody>
                {data.holdings.map((h) => (
                  <tr key={h.symbol}>
                    <td><SymLink sym={h.symbol} /></td><td>{h.since}</td>
                    <td>₹{num(h.invested, 0)}</td><td>{h.fill_price != null ? num(h.fill_price) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="empty">Nothing yet: the book holds cash until its first rebalance ({day(data.next_rebalance)} close).</p>}
        {data.holdings && data.holdings.length > 0 && (
          <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
            Cash not invested: ₹{num(data.cash, 0)}. Book value {money((data.book_value || 0) - (data.capital || 0))} on
            ₹{num(data.capital, 0)}.
          </p>
        )}
      </section>

      {data.waiting_orders && data.waiting_orders.length ? (
        <section className="mb-section">
          <h3>Orders waiting</h3>
          <p className="muted" style={{ marginTop: -4 }}>
            An order is not filled on a day the stock closes locked at its price band or does not trade. It is tried
            again each session. A buy is given up after five sessions; a sell waits until it fills.
          </p>
          <div className="table-wrap">
            <table className="datatable">
              <thead><tr><th>Order</th><th>Stock</th><th>Ordered</th><th>Why it waits</th></tr></thead>
              <tbody>
                {data.waiting_orders.map((o) => (
                  <tr key={`${o.side}-${o.symbol}`}>
                    <td className={o.side === "BUY" ? "up" : "down"}>{o.side === "BUY" ? "Buy" : "Sell"}</td>
                    <td><SymLink sym={o.symbol} /></td><td>{o.ordered}</td>
                    <td>{WHY[o.reason] || "Not tried yet"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="mb-section">
        <h3>Recent trades</h3>
        {data.recent_trades && data.recent_trades.length ? (
          <div className="table-wrap">
            <table className="datatable">
              <thead><tr><th>Date</th><th>Side</th><th>Stock</th><th>Value</th><th>Charges and slippage</th><th>Note</th></tr></thead>
              <tbody>
                {[...data.recent_trades].reverse().map((t, i) => {
                  const [cls, sideLabel] = SIDE[t.side] || ["muted", t.side];
                  return (
                    <tr key={`${t.date}-${t.symbol}-${i}`}>
                      <td>{t.date}</td><td className={cls}>{sideLabel}</td>
                      <td><SymLink sym={t.symbol} /></td><td>₹{num(t.value, 0)}</td>
                      <td className="muted">{t.side === "CANCELLED BUY" ? "—" : `₹${num(t.cost, 2)}`}</td>
                      <td className="muted">{tradeNote(t)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : <p className="empty">No trades yet.</p>}
      </section>

      <p className="muted" style={{ fontSize: 12, marginTop: 20 }}>
        After each rebalance, and when the evening job fails or stops early, one line goes to the activity log and, when
        Telegram is set up, to the phone.
        {" "}Last session processed: {data.last_processed || "—"} · latest NSE file: {data.latest_session || "—"} · updated {data.updated_at || "—"}
        {" "}· corporate-actions file from {checks.corporate_actions_as_of ? checks.corporate_actions_as_of.replace("T", " ") : "—"}
        {checks.corporate_actions_refreshed === false && <span className="down"> (the last refresh failed)</span>}.
        Prices are NSE&apos;s daily bhavcopies, trade-for-trade rows included, adjusted with NSE&apos;s corporate-actions file.
        Fills are at the next session&apos;s close, unless the stock is locked at its band or did not trade.
        Rules and evidence: docs/research/results-3i-momentum-corrected-data.md and results-universe-width.md.
      </p>
    </>
  );
}
