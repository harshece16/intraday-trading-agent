import { clock } from "../format";
import { activityKeys, KIND_TEXT } from "../helpers";
import SymLink from "./SymLink";

export default function Feed({ items }) {
  if (!items || !items.length) return <p className="empty">Nothing yet. Scans, picks and trades will appear here.</p>;
  const keys = activityKeys(items);
  return (
    <ul className="feed">
      {items.map((a, i) => (
        <li key={keys[i]}>
          <div className="meta">
            <span><span className={`kind ${a.kind}`}>{KIND_TEXT[a.kind] || a.kind}</span>{a.symbol ? <> <SymLink sym={a.symbol} /></> : null}</span>
            <span>{clock(a.ts)}</span>
          </div>
          <div className="body">{a.message}</div>
        </li>
      ))}
    </ul>
  );
}
