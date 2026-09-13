import { shortSource } from "../helpers";

export function RuleTag({ text }) {
  if (!text) return null;
  return <span className="rule-tag" title="From this stock's Trader Brain read">{text}</span>;
}

// One chip per distinct source, so it's obvious at a glance which book or
// technique justifies this stock's call — not just buried in the checklist.
export default function RuleBook({ r, b }) {
  const chips = [];
  const seen = new Set();
  const add = (label, detail) => {
    if (seen.has(label)) return;
    seen.add(label);
    chips.push({ label, detail });
  };
  if (b && b.checklist) {
    const side = r && r.side ? r.side.toLowerCase() : b.bias === "short" ? "short" : "long";
    const cl = b.checklist[side] || b.checklist.long;
    (cl ? cl.items : []).forEach((it) => add(shortSource(it.source), it.detail));
  }
  (r?.swing_patterns || []).forEach((sw) =>
    add("Bulkowski, Encyclopedia of Chart Patterns", `Confirmed ${sw.name} on the daily chart`)
  );
  if (b) add("Van Tharp, Trade Your Way to Financial Freedom", "Percent Risk Model position sizing");
  if (!chips.length) return null;
  return (
    <div className="rulebook">
      <div className="rulebook-label">Rule book used for this call</div>
      <div className="rb-row">
        {chips.map((c) => (
          <div className="rb-chip" title={c.detail || ""} key={c.label}>
            <b>{c.label}</b>
            <span>{c.detail || ""}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
