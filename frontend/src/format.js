export function num(n, d = 2) {
  return n === null || n === undefined || Number.isNaN(Number(n))
    ? "—"
    : Number(n).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
}
export function pct(n, d = 1) {
  return n === null || n === undefined ? "—" : `${n >= 0 ? "+" : ""}${Number(n).toFixed(d)}%`;
}
export function signed(n, d = 2) {
  return n === null || n === undefined ? "—" : `${n >= 0 ? "+" : ""}${Number(n).toFixed(d)}`;
}
export function tone(n) {
  return n > 0 ? "up" : n < 0 ? "down" : "";
}
export function money(n) {
  if (n === null || n === undefined) return "—";
  return `${n < 0 ? "−" : n > 0 ? "+" : ""}₹${Math.abs(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
/** A balance, limit or price in rupees: never a "+" sign, which reads as a
 *  gain (#243). Use money() only for P&L. */
export function inr(n, d = 0) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  return `${v < 0 ? "−" : ""}₹${Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
}

// Every clock in IST, 24-hour, the way the engine writes its own times
// ("15:08", "09:45"). They used to follow the browser's zone (#243).
const IST = "Asia/Kolkata";
const HM = new Intl.DateTimeFormat("en-IN", { timeZone: IST, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const HMS = new Intl.DateTimeFormat("en-IN", { timeZone: IST, hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
const DAY_MONTH = new Intl.DateTimeFormat("en-IN", { timeZone: IST, day: "numeric", month: "short" });
const YMD = new Intl.DateTimeFormat("en-CA", { timeZone: IST, year: "numeric", month: "2-digit", day: "2-digit" });

function toDate(t) {
  if (t === null || t === undefined || t === "") return null;
  const d = typeof t === "number" ? new Date(t * 1000) : new Date(t);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "14:32" in IST, from epoch seconds or an ISO string. */
export function clock(t) {
  const d = toDate(t);
  return d ? HM.format(d) : "—";
}
/** "14:32 IST", for a time shown on its own. */
export function clockIST(t) {
  const d = toDate(t);
  return d ? `${HM.format(d)} IST` : "—";
}
/** "14:32:05" in IST. */
export function hms(t) {
  const d = toDate(t);
  return d ? HMS.format(d) : "—";
}
/** "5 Oct, 14:32 IST". */
export function dateTimeIST(t) {
  const d = toDate(t);
  return d ? `${DAY_MONTH.format(d)}, ${HM.format(d)} IST` : "—";
}
/** The IST calendar day, "2026-10-05". */
export function istDay(t) {
  const d = toDate(t);
  return d ? YMD.format(d) : "";
}
export function dateLabel(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}
export function safeUrl(u) {
  return typeof u === "string" && /^https?:\/\//i.test(u) ? u : null;
}
export function joinWords(arr) {
  if (!arr || !arr.length) return "";
  if (arr.length === 1) return arr[0];
  return `${arr.slice(0, -1).join(", ")} and ${arr[arr.length - 1]}`;
}

export const GLOSSARY = {
  vwap: "Volume-Weighted Average Price — the average price today, weighted by how much traded at each level. The intraday institutional benchmark.",
  ema20: "20-period Exponential Moving Average — a trend line that weights recent candles more heavily than a simple average.",
  ema50: "50-period Exponential Moving Average — the slower trend line; price crossing both 20 and 50 EMA in order signals a stronger trend.",
  rsi: "Relative Strength Index — momentum on a 0-100 scale. Above 70 is often called overbought, below 30 oversold, but this app reads it differently depending on trend vs range.",
  macd: "Moving Average Convergence/Divergence — the gap between a fast and slow EMA, used to spot momentum shifts.",
  adx: "Average Directional Index (Wilder) — measures trend strength (not direction) on a 0-100 scale. Above 25 is usually called trending, below 20 ranging.",
  atr: "Average True Range — the average size of a candle over N periods. Used here to size stops relative to how much a stock actually moves.",
  bollinger: "Bollinger Bands — a band 2 standard deviations above/below a 20-period average. Price touching the edge is read differently in a trend vs a range.",
  stochastic: "Stochastic oscillator — compares the close to its recent high-low range, on a 0-100 scale, to spot momentum turns.",
  rrr: "Reward-to-Risk Ratio — the target distance divided by the stop distance. 1.5 means risking ₹1 to make ₹1.50.",
  nr7: "Narrowest Range in 7 — today's daily range is the tightest of the last 7 sessions, often read as compression before a bigger move.",
  cpr: "Central Pivot Range — pivot, top (TC) and bottom (BC) levels computed from the previous session's high/low/close.",
  fib: "Fibonacci retracement — levels (23.6%, 38.2%, 50%, 61.8%) where a pullback within a trend often pauses.",
  obv: "On Balance Volume — cumulative volume, added on up-closes and subtracted on down-closes. Its trend should agree with price; when it doesn't, that's a warning (Murphy, ch 7).",
  mis: "Margin Intraday Squareoff — a leveraged intraday order type that must be closed the same day, or the broker auto-squares it off.",
  delta: "Change in an option's premium per ₹1 move in the underlying. Roughly, the odds the option finishes in-the-money.",
  gamma: "Change in an option's Delta per ₹1 move in the underlying — how fast Delta itself is changing.",
  theta: "Change in an option's premium per day closer to expiry — time decay. Always working against an option buyer.",
  vega: "Change in an option's premium per 1-point change in implied volatility.",
  iv: "Implied Volatility — the volatility level the market is pricing into an option's premium, solved backwards from that premium (this app doesn't get IV directly from Kite).",
  dsr: "Deflated Sharpe Ratio (Bailey & López de Prado) — corrects a backtest's Sharpe ratio for how many configurations were already tried, since trying enough eventually looks good by chance alone.",
  ic: "Information Coefficient (Grinold) — rank correlation between a score and what actually happened next. 0 = no predictive power, ±1 = perfect.",
  kelly: "Kelly fraction — the mathematically optimal bet size given a system's win rate and average win/loss. Negative means the correct size is zero.",
  expectancy: "Average result per trade, in R (multiples of what was risked). Positive means the system wins more than it loses, on average, after costs.",
  confidence: "A composite of how strong today's setup looks AND whether the system has actually proven an edge yet — not a probability of profit (see the Technical Analysis page).",
};
