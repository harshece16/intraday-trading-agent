export function SidePill({ side, suffix = "" }) {
  return <span className={`pill ${side === "SHORT" ? "short" : "long"}`}>{side === "SHORT" ? "Short" : "Long"}{suffix}</span>;
}

export function BiasPill({ bias }) {
  const cls = bias === "bullish" || bias === "long" ? "long" : bias === "bearish" || bias === "short" ? "short" : "neutral";
  return <span className={`pill ${cls}`}>{bias || "neutral"}</span>;
}

export function StatusPill({ status }) {
  if (status === "pass") return <span className="pill long">pass</span>;
  if (status === "fail") return <span className="pill short">fail</span>;
  return <span className="pill neutral">not enough data</span>;
}

export function ConfidencePill({ score }) {
  const cls = score >= 75 ? "long" : score >= 50 ? "wait" : score >= 25 ? "neutral" : "short";
  return <span className={`pill ${cls}`}>{score}/100</span>;
}
