import { Link } from "react-router-dom";

const README = "https://github.com/harshece16/intraday-trading-agent/blob/main/README.md";
const REPO = "https://github.com/harshece16/intraday-trading-agent/blob/main";

// The README sections that record the intraday verdict, and the decision
// that followed it (README section 116).
const SOURCES = [
  ["§88", `${README}#88-what-should-decide-when-to-trade-now-the-checklist-is-retired-intraday-nothing-clears-costs-positional-how-much-momentum-to-hold`],
  ["§104", `${README}#104-the-night-of-2026-09-29-eight-forecasting-models-and-75-combinations-tested-none-pays`],
  ["§109", `${README}#109-market-breadth-and-intermarket-moves-measured-run-2026-09-25-merged-2026-09-30-neither-predicts-the-session-by-enough-to-trade`],
  ["§116", `${README}#116-the-momentum-book-is-the-strategy-the-intraday-engine-is-a-paper-record`],
  ["trial log", `${REPO}/docs/research/trials.md`],
];

/** Opens every page of the intraday engine: it is a paper record, not the
 * strategy. Informational only; it changes nothing the engine does. */
export default function IntradayRecordBanner() {
  return (
    <aside className="record-banner" aria-label="About the intraday pages">
      <p>
        <strong>Intraday paper record.</strong> No intraday edge was found: 202 strategy trials and research
        looks L40 to L51 found nothing that pays the ~16.6 bp round trip. The intraday engine keeps running in
        paper, unchanged, as a record.
        {" "}The strategy is the monthly <Link to="/">momentum book</Link>.
      </p>
      <p className="record-banner-src">
        Sources:{" "}
        {SOURCES.map(([label, href], i) => (
          <span key={label}>
            {i ? " · " : ""}
            <a href={href} target="_blank" rel="noreferrer">{label}</a>
          </span>
        ))}
      </p>
    </aside>
  );
}
