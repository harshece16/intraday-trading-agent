import { useEffect, useRef, useState } from "react";
import {
  createChart, CandlestickSeries, LineSeries, HistogramSeries,
  LineStyle, CrosshairMode, createSeriesMarkers,
} from "lightweight-charts";
import { apiFetch, IST_OFFSET_S } from "../api";
import { num } from "../format";

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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
 */
export default function Chart({ symbol, plan, position, patterns, barTime, trades, className = "stk-chart" }) {
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

  // Create the chart once.
  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const chart = createChart(el, {
      layout: { background: { color: "transparent" }, textColor: cssVar("--ink-3"), fontFamily: cssVar("--font"), fontSize: 11 },
      grid: { vertLines: { visible: false }, horzLines: { color: cssVar("--rule") } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
      crosshair: { mode: CrosshairMode.Normal },
      kineticScroll: { mouse: true, touch: true },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });
    const up = cssVar("--long"), down = cssVar("--short");
    const series = chart.addSeries(CandlestickSeries, { upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down, lastValueVisible: false });
    series.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });
    const ema20 = chart.addSeries(LineSeries, { color: cssVar("--focus"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const ema50 = chart.addSeries(LineSeries, { color: cssVar("--book"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const stUp = chart.addSeries(LineSeries, { color: cssVar("--long"), lineWidth: 3, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const stDown = chart.addSeries(LineSeries, { color: cssVar("--short"), lineWidth: 3, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "vol", priceLineVisible: false, lastValueVisible: false });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
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
  }, []);

  // Fetch + set candle/EMA/volume data when the symbol changes.
  useEffect(() => {
    if (!symbol || !seriesRef.current) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/api/candles/${encodeURIComponent(symbol)}`);
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
        chartRef.current?.timeScale().fitContent();
      } catch (e) {
        /* the backend may not have candles for this stock yet */
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  // Real position lines (bought/now/stop/target) when one's open here,
  // otherwise the checklist's hypothetical entry/stop/target/support/
  // resistance/VWAP for a setup not yet taken.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    priceLinesRef.current.forEach((l) => series.removePriceLine(l));
    priceLinesRef.current = [];
    const add = (price, color, title, dashed = true) => {
      if (price != null) {
        priceLinesRef.current.push(
          series.createPriceLine({ price, color, lineWidth: dashed ? 1 : 2, lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid, axisLabelVisible: true, title })
        );
      }
    };

    const held = position && position.quantity;
    if (held) {
      const side = position.quantity > 0 ? "long" : "short";
      add(position.avg_price, cssVar("--wait"), `Bought (${side})`, false);
      add(position.ltp, cssVar("--book"), "Now", false);
      add(position.stop_price, cssVar("--short"), "Stop", false);
      add(position.target_price, cssVar("--long"), "Target", false);
      return;
    }

    if (!plan) return;
    add(plan.support, cssVar("--long"), "Support");
    add(plan.resistance, cssVar("--short"), "Resistance");
    add(plan.vwap, cssVar("--focus"), "VWAP");
    if (plan.cl && plan.cl.stop != null) {
      add(plan.cl.entry, cssVar("--ink-2"), `Plan entry (${plan.side})`, false);
      add(plan.cl.stop, cssVar("--short"), `Stop (${plan.cl.rrr != null ? "RRR " + num(plan.cl.rrr, 1) : "risk"})`, false);
      add(plan.cl.target, cssVar("--long"), "Target", false);
    }
  }, [plan, position]);

  // Latest candlestick pattern marker(s) plus a BUY/SELL tag at every real
  // trade fill in this stock (from the trade journal — never a hypothetical
  // signal), merged into one time-sorted marker set.
  useEffect(() => {
    const markers = markersRef.current;
    if (!markers) return;
    const list = [];
    if (patterns && patterns.length && barTime) {
      const time = Math.floor(new Date(barTime).getTime() / 1000) + IST_OFFSET_S;
      for (const p of patterns) {
        list.push({
          time,
          position: p.bias === "bearish" ? "aboveBar" : "belowBar",
          color: p.bias === "bearish" ? cssVar("--short") : p.bias === "bullish" ? cssVar("--long") : cssVar("--ink-3"),
          shape: p.bias === "bearish" ? "arrowDown" : p.bias === "bullish" ? "arrowUp" : "circle",
          text: p.name,
        });
      }
    }
    if (trades && trades.length && symbol && timesRef.current.length) {
      for (const t of trades) {
        if (t.symbol !== symbol) continue;
        const time = nearestTime(timesRef.current, Math.floor(t.ts) + IST_OFFSET_S);
        const buy = t.side === "BUY";
        list.push({
          time,
          position: buy ? "belowBar" : "aboveBar",
          color: buy ? cssVar("--long") : cssVar("--short"),
          shape: buy ? "arrowUp" : "arrowDown",
          text: buy ? "BUY" : "SELL",
        });
      }
    }
    list.sort((a, b) => a.time - b.time);
    markers.setMarkers(list);
  }, [patterns, barTime, trades, symbol, candleTick]);

  return <div className={className} ref={elRef} />;
}
