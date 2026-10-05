// The one vocabulary for the process log (README section 125). Book and kind
// come from the backend; these are their labels on the page. Kept apart from
// the components so fast refresh keeps working.
export const BOOK_TEXT = { intraday: "Intraday", jev: "Jev", jev2: "Jev 2", rule_lab: "Rule lab", momentum: "Momentum" };
export const BOOK_ORDER = ["intraday", "jev", "jev2", "rule_lab", "momentum"];
export const KIND_LABEL = {
  scan: "Scan", watchlist: "Watchlist", setup: "Setup", blocked: "Skipped", review: "Review", trade: "Trade",
  risk: "Risk", error: "Problem", system: "System", summary: "Summary", kite_preopen: "Kite login",
  round: "Round", decision: "Decision", session: "Session", lab_entry: "Trades opened", lab_exit: "Trades closed",
  job: "Job", alert: "Alert", rebalance: "Rebalance",
};

export function kindLabel(k) {
  return KIND_LABEL[k] || k;
}
