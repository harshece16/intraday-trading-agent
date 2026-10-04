import { useEffect, useRef, useState } from "react";
import {
  createChart, CandlestickSeries, LineSeries, HistogramSeries,
  LineStyle, CrosshairMode, createSeriesMarkers,
} from "lightweight-charts";
import { apiFetch, IST_OFFSET_S, useVisibleInterval } from "../api";
import { num } from "../format";

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// Theme colours, read once per chart: getComputedStyle used to run for every
// candle's volume bar and every price line on each 3 s state push.
const TOKENS = ["--ink-2", "--ink-3", "--rule", "--long", "--short", "--long-bg", "--short-bg", "--wait", "--book", "--focus", "--font"];
function readColors() {
  return Object.fromEntries(TOKENS.map((t) => [t, cssVar(t)]));
}

// Same formula as backend/indicators.py's ema_series() — recomputed client-side
// from the same candles already on the chart, not a separate/guessed value.
function emaSeriesJS(values, period) {
  const out = new Array(values.length).fill(null);
  if (values.length < period) return out;
  const k = 2 / (period + 1);
  let e = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  out[period - 1] = e;
  for (let i = period; i < values.length; i++) {
    e = values[i] * k + e * (1 - k);
    out[i] = e;
  }
  return out;
}

// Classic ATR-based Supertrend (period, multiplier): a trailing stop band
// that sits below price in an uptrend and above it in a downtrend, flipping
// side whenever a close breaks through it. Same Wilder-ATR / true-range
// math as backend/indicators.py's atr(), just extended into a per-bar
// series and recomputed client-side from the same real candles already on
// the chart — same convention as emaSeriesJS above, not a separate source.
function supertrendJS(candles, period = 10, multiplier = 3) {
  const n = candles.length;
  const trend = new Array(n).fill(null); // 1 = up, -1 = down
  const value = new Array(n).fill(null);
  if (n < period + 1) return { trend, value };

  const atr = new Array(n).fill(null);
  let trSum = 0;
  for (let i = 1; i <= period; i++) {
    const h = candles[i].high, l = candles[i].low, pc = candles[i - 1].close;
    trSum += Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
  }
  atr[period] = trSum / period;
  for (let i = period + 1; i < n; i++) {
    const h = candles[i].high, l = candles[i].low, pc = candles[i - 1].close;
    const tr = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
    atr[i] = (atr[i - 1] * (period - 1) + tr) / period;
  }

  let finalUpper = null, finalLower = null, dir = 1;
  for (let i = period; i < n; i++) {
    if (atr[i] == null) continue;
    const mid = (candles[i].high + candles[i].low) / 2;
    const basicUpper = mid + multiplier * atr[i];
    const basicLower = mid - multiplier * atr[i];
    if (finalUpper == null) {
      finalUpper = basicUpper;
      finalLower = basicLower;
    } else {
      const prevClose = candles[i - 1].close;
      finalUpper = basicUpper < finalUpper || prevClose > finalUpper ? basicUpper : finalUpper;
      finalLower = basicLower > finalLower || prevClose < finalLower ? basicLower : finalLower;
    }
    const close = candles[i].close;
    if (dir === 1 && close < finalLower) dir = -1;
    else if (dir === -1 && close > finalUpper) dir = 1;
    trend[i] = dir;
    value[i] = dir === 1 ? finalLower : finalUpper;
  }
  return { trend, value };
}

// Snaps an arbitrary unix time (e.g. a trade fill) onto the nearest candle
// time already on the chart — lightweight-charts markers need to land on an
// actual data point, and a trade's exact second rarely matches a 5m bar.
// A token colour with an alpha channel, for lines that should sit behind the
// candles rather than on top of them. Tokens are "#RRGGBB"; anything else is
// returned unchanged.
function withAlpha(color, alpha) {
  return /^#[0-9a-f]{6}$/i.test(color) ? color + Math.round(alpha * 255).toString(16).padStart(2, "0") : color;
}

// Index of the first bar of the Nth-from-last session in a list of candle
// time strings ("YYYY-MM-DDTHH:MM..."), so the chart can open on today
// instead of squeezing every fetched day into one frame.
function sessionStart(candles, sessions) {
  const days = [];
  for (let i = candles.length - 1; i >= 0; i--) {
    const d = String(candles[i].time).slice(0, 10);
    if (days[days.length - 1] !== d) {
      if (days.length === sessions) return i + 1;
      days.push(d);
    }
  }
  return 0;
}

// Price lines that land on the same price (the checklist's target is often
// the resistance it's aiming at) are drawn once, with both names, instead of
// two axis labels stacked on top of each other.
function mergeLines(lines) {
  const out = [];
  for (const l of lines) {
    if (l.price == null) continue;
    const same = out.find((o) => Math.abs(o.price - l.price) <= Math.abs(l.price) * 0.0001);
    if (same) same.title = `${same.title} · ${l.title}`;
    else out.push({ ...l });
  }
  return out;
}

function nearestTime(times, t) {
  if (!times.length) return t;
  let best = times[0], bestDiff = Math.abs(times[0] - t);
  for (let i = 1; i < times.length; i++) {
    const diff = Math.abs(times[i] - t);
    if (diff < bestDiff) { best = times[i]; bestDiff = diff; }
  }
  return best;
}

/**
 * The stock chart: candles, EMA 20/50, a volume panel, and labeled price
 * lines — either the checklist's hypothetical entry/stop/target for a
 * setup not yet taken, OR, when `position` is a real open position in
 * this stock, the actual bought price, current price and the real
 * stop/target that will actually close it — never both at once, since
 * once a position is open the checklist keeps re-evaluating a fresh
 * hypothetical entry every tick that has nothing to do with the trade
 * that's already live. Also markers for the latest candlestick pattern and
 * for every real BUY/SELL fill in this stock (from the trade journal, not
 * hypothetical), plus a Supertrend band (ATR trailing stop, flips side on a
 * close through it) tracking price as a green/red line.
 * Deliberately does NOT draw a projected future price path — this app has
 * no calibrated forecasting model (the Dimaag Scorecard's Information
 * Coefficient needs 20+ separate sessions before it means anything, see
 * README §38), so what's shown is always a real, computed number, never a
 * price prediction.
 *
 * `compact` is the Overview tile: the latest session only, no volume or
 * Supertrend, price lines without axis labels (the card's text gives the
 * numbers), and no wheel/drag handling so scrolling the page still scrolls
 * the page.
 */
export default function Chart({ symbol, plan, position, patterns, barTime, trades, className = "stk-chart", compact = false }) {
  const elRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const ema20Ref = useRef(null);
  const ema50Ref = useRef(null);
  const stUpRef = useRef(null);
  const stDownRef = useRef(null);
  const volumeRef = useRef(null);
  const markersRef = useRef(null);
  const priceLinesRef = useRef([]);
  const timesRef = useRef([]);
  // Bumped once real candle times are in timesRef, so the trade-marker
  // effect (which snaps onto those times) re-runs after this async fetch —
  // timesRef itself is a ref, so writing it alone wouldn't trigger a re-run.
  const [candleTick, setCandleTick] = useState(0);
  const colorsRef = useRef(null);
  const nowLineRef = useRef(null);
  const rangeSetForRef = useRef(null); // the symbol whose opening zoom has been set
  // Live candles: refetch every 60 s while the tab is visible, and when the
  // engine reports a new bar. They used to load once per symbol (#perf F1).
  const [refreshTick, setRefreshTick] = useState(0);
  useVisibleInterval(() => setRefreshTick((n) => n + 1), symbol ? 60000 : null);

  // Create the chart once.
  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const col = (colorsRef.current = readColors());
    const cssVar = (t) => col[t];
    // attributionLogo is off: the TradingView credit the library's licence asks
    // for is a text link on each page that shows a chart instead.
    const chart = createChart(el, {
      layout: { background: { color: "transparent" }, textColor: cssVar("--ink-3"), fontFamily: cssVar("--font"),
                fontSize: compact ? 10 : 11, attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: withAlpha(cssVar("--rule"), 0.6) } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, rightOffset: compact ? 2 : 6 },
      crosshair: { mode: compact ? CrosshairMode.Hidden : CrosshairMode.Normal },
      kineticScroll: { mouse: !compact, touch: !compact },
      handleScroll: compact ? false : { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: compact ? false : { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });
    const up = cssVar("--long"), down = cssVar("--short");
    const series = chart.addSeries(CandlestickSeries, { upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down, lastValueVisible: false });
    series.priceScale().applyOptions({ scaleMargins: compact ? { top: 0.1, bottom: 0.08 } : { top: 0.08, bottom: 0.22 } });
    const ema20 = chart.addSeries(LineSeries, { color: cssVar("--focus"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const ema50 = chart.addSeries(LineSeries, { color: cssVar("--book"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    // Supertrend and volume are context for a full-size read; on a 300px tile
    // they bury the candles, so the tile leaves them out.
    const band = { lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false };
    const stUp = compact ? null : chart.addSeries(LineSeries, { ...band, color: withAlpha(cssVar("--long"), 0.55) });
    const stDown = compact ? null : chart.addSeries(LineSeries, { ...band, color: withAlpha(cssVar("--short"), 0.55) });
    const volume = compact ? null : chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "vol", priceLineVisible: false, lastValueVisible: false });
    volume?.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const markers = createSeriesMarkers(series, []);

    chartRef.current = chart;
    seriesRef.current = series;
    ema20Ref.current = ema20;
    ema50Ref.current = ema50;
    stUpRef.current = stUp;
    stDownRef.current = stDown;
    volumeRef.current = volume;
    markersRef.current = markers;

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch + set candle/EMA/volume data: on a new symbol, a new bar, and every
  // 60 s while visible.
  useEffect(() => {
    if (!symbol || !seriesRef.current) return;
    let cancelled = false;
    const cssVar = (t) => colorsRef.current[t];
    (async () => {
      try {
        const res = await apiFetch(`/api/candles/${encodeURIComponent(symbol)}`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        const candles = data.candles || [];
        const times = candles.map((c) => Math.floor(new Date(c.time).getTime() / 1000) + IST_OFFSET_S);
        seriesRef.current.setData(candles.map((c, i) => ({ time: times[i], open: c.open, high: c.high, low: c.low, close: c.close })));
        timesRef.current = times;
        setCandleTick((n) => n + 1);
        const closes = candles.map((c) => c.close);
        const e20 = emaSeriesJS(closes, 20), e50 = emaSeriesJS(closes, 50);
        ema20Ref.current?.setData(times.map((t, i) => ({ time: t, value: e20[i] })).filter((p) => p.value != null));
        ema50Ref.current?.setData(times.map((t, i) => ({ time: t, value: e50[i] })).filter((p) => p.value != null));
        const st = supertrendJS(candles, 10, 3);
        stUpRef.current?.setData(times.map((t, i) => ({ time: t, value: st.trend[i] === 1 ? st.value[i] : null })).filter((p) => p.value != null));
        stDownRef.current?.setData(times.map((t, i) => ({ time: t, value: st.trend[i] === -1 ? st.value[i] : null })).filter((p) => p.value != null));
        volumeRef.current?.setData(
          candles.map((c, i) => ({ time: times[i], value: c.volume || 0, color: c.close >= c.open ? cssVar("--long-bg") : cssVar("--short-bg") }))
        );
        // Open on the latest session (two on the full chart). Earlier bars are
        // still loaded, and the full chart can scroll back to them. Only on the
        // first load of a symbol, so a refresh keeps the user's zoom.
        if (candles.length && rangeSetForRef.current !== symbol) {
          const from = sessionStart(candles, compact ? 1 : 2);
          chartRef.current?.timeScale().setVisibleLogicalRange({ from: from - 0.5, to: candles.length - 1 + (compact ? 2 : 6) });
          rangeSetForRef.current = symbol;
        }
      } catch (e) {
        /* the backend may not have candles for this stock yet */
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, barTime, refreshTick]);

  // Real position lines (bought/now/stop/target) when one's open here,
  // otherwise the checklist's hypothetical entry/stop/target/support/
  // resistance/VWAP for a setup not yet taken. Built from primitives and keyed
  // on them, so a state push with the same numbers redraws nothing; the "Now"
  // line only moves (applyOptions).
  const held = !!(position && position.quantity);
  const lineSpec = [];
  const add = (price, color, title, dashed = true) => lineSpec.push({ price: price ?? null, color, title, dashed });
  if (held) {
    const side = position.quantity > 0 ? "long" : "short";
    add(position.avg_price, "--wait", `Bought (${side})`, false);
    add(position.stop_price, "--short", "Stop", false);
    add(position.target_price, "--long", "Target", false);
  } else if (plan) {
    // The tile keeps only the trade plan itself; support, resistance and
    // VWAP are the full chart's context.
    if (!compact) {
      add(plan.support, "--long", "Support");
      add(plan.resistance, "--short", "Resistance");
      add(plan.vwap, "--focus", "VWAP");
    }
    if (plan.cl && plan.cl.stop != null) {
      add(plan.cl.entry, "--ink-2", `Plan entry (${plan.side})`, false);
      add(plan.cl.stop, "--short", `Stop (${plan.cl.rrr != null ? "R:R " + num(plan.cl.rrr, 1) : "risk"})`, false);
      add(plan.cl.target, "--long", "Target", false);
    }
  }
  const linesKey = JSON.stringify([held, compact, lineSpec]);
  const nowPrice = held ? position.ltp ?? null : null;

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    const [isHeld, isCompact, spec] = JSON.parse(linesKey);
    const col = colorsRef.current;
    priceLinesRef.current.forEach((l) => series.removePriceLine(l));
    priceLinesRef.current = [];
    nowLineRef.current = null;
    const make = (l) => series.createPriceLine({
      price: l.price, color: col[l.color], lineWidth: l.dashed ? 1 : isCompact ? 1 : 2,
      lineStyle: l.dashed ? LineStyle.Dashed : LineStyle.Solid,
      axisLabelVisible: !isCompact, title: isCompact ? "" : l.title,
    });
    for (const l of mergeLines(spec)) priceLinesRef.current.push(make(l));
    if (isHeld) {
      nowLineRef.current = make({ price: 0, color: "--book", title: "Now", dashed: false });
      priceLinesRef.current.push(nowLineRef.current);
    }
  }, [linesKey]);

  useEffect(() => {
    const line = nowLineRef.current;
    if (!line) return;
    if (nowPrice == null) line.applyOptions({ lineVisible: false, axisLabelVisible: false });
    else line.applyOptions({ price: nowPrice, lineVisible: true, axisLabelVisible: !compact });
  }, [nowPrice, linesKey, compact]);

  // Latest candlestick pattern marker(s) plus a BUY/SELL tag at every real
  // trade fill in this stock (from the trade journal — never a hypothetical
  // signal), merged into one time-sorted marker set.
  const markerKey = JSON.stringify([
    compact, barTime || null,
    (patterns || []).map((p) => [p.name, p.bias]),
    symbol ? (trades || []).filter((t) => t.symbol === symbol).map((t) => [t.ts, t.side]) : [],
  ]);
  useEffect(() => {
    const markers = markersRef.current;
    if (!markers) return;
    const [isCompact, bar, pats, fills] = JSON.parse(markerKey);
    const col = colorsRef.current;
    const list = [];
    if (pats.length && bar) {
      const time = Math.floor(new Date(bar).getTime() / 1000) + IST_OFFSET_S;
      for (const [name, bias] of pats) {
        list.push({
          time,
          position: bias === "bearish" ? "aboveBar" : "belowBar",
          color: bias === "bearish" ? col["--short"] : bias === "bullish" ? col["--long"] : col["--ink-3"],
          shape: bias === "bearish" ? "arrowDown" : bias === "bullish" ? "arrowUp" : "circle",
          // The latest bar sits at the tile's right edge, where a pattern name
          // gets cut off; the tile keeps the arrow and the full chart the name.
          text: isCompact ? "" : name,
        });
      }
    }
    if (fills.length && timesRef.current.length) {
      for (const [ts, side] of fills) {
        const time = nearestTime(timesRef.current, Math.floor(ts) + IST_OFFSET_S);
        const buy = side === "BUY";
        list.push({
          time,
          position: buy ? "belowBar" : "aboveBar",
          color: buy ? col["--long"] : col["--short"],
          shape: buy ? "arrowUp" : "arrowDown",
          text: buy ? "BUY" : "SELL",
        });
      }
    }
    list.sort((a, b) => a.time - b.time);
    markers.setMarkers(list);
  }, [markerKey, candleTick]);

  return <div className={className} ref={elRef} />;
}
