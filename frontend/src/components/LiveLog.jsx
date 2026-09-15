import { useEffect, useRef } from "react";
import { KIND_TEXT } from "../helpers";

function hms(t) {
  return new Date(t * 1000).toLocaleTimeString([], { hour12: false });
}

/** A terminal-style live log — the same activity stream Feed.jsx shows on
 * Overview, but full-history, auto-scrolling, and available from any page
 * (a fixed bottom drawer, not tied to navigation). No polling: it's the
 * same WebSocket-pushed state every page already reads, just rendered as a
 * console instead of a card list. */
export default function LiveLog({ state: s, open, onClose }) {
  const bodyRef = useRef(null);
  const stickToBottom = useRef(true);
  const items = [...(s?.activity || [])].reverse(); // oldest -> newest, terminal order

  useEffect(() => {
    if (!open) return;
    const el = bodyRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [items.length, open]);

  function handleScroll() {
    const el = bodyRef.current;
    if (!el) return;
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  }

  if (!open) return null;

  return (
    <div className="live-log">
      <div className="live-log-bar">
        <span>Live log — {items.length ? `${items.length} events` : "waiting for activity…"}</span>
        <button className="btn" onClick={onClose}>Close</button>
      </div>
      <div className="live-log-body" ref={bodyRef} onScroll={handleScroll}>
        {items.length ? (
          items.map((a, i) => (
            <div className="live-log-line" key={i}>
              <span className="live-log-ts">{hms(a.ts)}</span>
              <span className={`kind ${a.kind}`}>[{KIND_TEXT[a.kind] || a.kind}]</span>
              {a.symbol && <span className="live-log-sym">{a.symbol}</span>}
              <span>{a.message}</span>
            </div>
          ))
        ) : (
          <div className="live-log-line muted">Nothing yet — scans, picks and trades will stream in here as they happen.</div>
        )}
      </div>
    </div>
  );
}
