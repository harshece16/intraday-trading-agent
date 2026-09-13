import { useEffect, useRef } from "react";
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

/**
 * The stock chart: candles, EMA 20/50, a volume panel, the checklist's
 * entry/stop/target as labeled price lines, and markers for the latest
 * candlestick pattern. Deliberately does NOT draw a projected future price
 * path — this app has no calibrated forecasting model (the Dimaag
 * Scorecard's Information Coefficient is currently negative), so what's
 * shown is the real, computed trade plan a checklist pass would use, never
 * a price prediction.
 */
export default function Chart({ symbol, plan, patterns, barTime }) {
  const elRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const ema20Ref = useRef(null);
  const ema50Ref = useRef(null);
  const volumeRef = useRef(null);
  const markersRef = useRef(null);
  const priceLinesRef = useRef([]);

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
    const series = chart.addSeries(CandlestickSeries, { upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down });
    series.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });
    const ema20 = chart.addSeries(LineSeries, { color: cssVar("--focus"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const ema50 = chart.addSeries(LineSeries, { color: cssVar("--book"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "vol", priceLineVisible: false, lastValueVisible: false });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const markers = createSeriesMarkers(series, []);

    chartRef.current = chart;
    seriesRef.current = series;
    ema20Ref.current = ema20;
    ema50Ref.current = ema50;
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
        const closes = candles.map((c) => c.close);
        const e20 = emaSeriesJS(closes, 20), e50 = emaSeriesJS(closes, 50);
        ema20Ref.current?.setData(times.map((t, i) => ({ time: t, value: e20[i] })).filter((p) => p.value != null));
        ema50Ref.current?.setData(times.map((t, i) => ({ time: t, value: e50[i] })).filter((p) => p.value != null));
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

  // Entry/stop/target/support/resistance/VWAP price lines.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    priceLinesRef.current.forEach((l) => series.removePriceLine(l));
    priceLinesRef.current = [];
    if (!plan) return;
    const add = (price, color, title, dashed = true) => {
      if (price) {
        priceLinesRef.current.push(
          series.createPriceLine({ price, color, lineWidth: dashed ? 1 : 2, lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid, axisLabelVisible: true, title })
        );
      }
    };
    add(plan.support, cssVar("--long"), "Support");
    add(plan.resistance, cssVar("--short"), "Resistance");
    add(plan.vwap, cssVar("--focus"), "VWAP");
    if (plan.cl && plan.cl.stop != null) {
      add(plan.cl.entry, cssVar("--ink-2"), `Plan entry (${plan.side})`, false);
      add(plan.cl.stop, cssVar("--short"), `Stop (${plan.cl.rrr != null ? "RRR " + num(plan.cl.rrr, 1) : "risk"})`, false);
      add(plan.cl.target, cssVar("--long"), "Target", false);
    }
  }, [plan]);

  // Latest candlestick pattern marker(s).
  useEffect(() => {
    const markers = markersRef.current;
    if (!markers) return;
    if (!patterns || !patterns.length || !barTime) {
      markers.setMarkers([]);
      return;
    }
    const time = Math.floor(new Date(barTime).getTime() / 1000) + IST_OFFSET_S;
    markers.setMarkers(
      patterns.map((p) => ({
        time,
        position: p.bias === "bearish" ? "aboveBar" : "belowBar",
        color: p.bias === "bearish" ? cssVar("--short") : p.bias === "bullish" ? cssVar("--long") : cssVar("--ink-3"),
        shape: p.bias === "bearish" ? "arrowDown" : p.bias === "bullish" ? "arrowUp" : "circle",
        text: p.name,
      }))
    );
  }, [patterns, barTime]);

  return <div id="stk-chart" ref={elRef} />;
}
