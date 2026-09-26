import { CHART, CHART_HOUR_LABEL_STEP, DEFAULT_DT_HOURS } from "../constants.js";
import { T } from "../strings.js";
import { state } from "../state.js";
import { $, h, svg, clear } from "../dom.js";

const SERIES = [["price_import", "line-imp"], ["price_export", "line-exp"], ["price_p2p", "line-p2p"]];
const HOURS_PER_DAY = 24;

function xOf(i, n) {
  return CHART.left + (i / Math.max(1, n - 1)) * (CHART.width - CHART.left - CHART.right);
}

// Domeniul valorilor cu 5 % margine, mereu incluzând 0.
function valueRange(prices) {
  const all = prices.flatMap((p) => SERIES.map(([k]) => Number(p[k]))).filter((v) => Number.isFinite(v));
  let min = Math.min(0, ...all), max = Math.max(...all);
  if (max - min < 1e-9) { min -= 0.1; max += 0.1; }
  const pad = (max - min) * 0.05;
  return { min: min - pad, max: max + pad };
}

export function renderPriceChart(data) {
  const box = $("priceChart");
  clear(box);
  const prices = data.prices || [];
  if (!prices.length) {
    box.appendChild(h("p", { class: "muted" }, T.noPrices));
    return;
  }
  const { min, max } = valueRange(prices);
  const n = prices.length;
  const x = (i) => xOf(i, n);
  const y = (v) => CHART.top + (1 - (v - min) / (max - min)) * (CHART.height - CHART.top - CHART.bottom);

  const el = svg("svg", { viewBox: "0 0 " + CHART.width + " " + CHART.height, class: "price-svg", role: "img" });
  el.appendChild(svg("title", {}, T.chartTitle));
  renderValueAxis(el, min, max, y);
  renderHourAxis(el, n, data.dt_hours || DEFAULT_DT_HOURS, x);
  for (const [key, cls] of SERIES) {
    const pts = prices.map((p, i) => x(i).toFixed(1) + "," + y(Number(p[key])).toFixed(1)).join(" ");
    el.appendChild(svg("polyline", { points: pts, class: "price-line " + cls }));
  }
  const cur = Math.min(n - 1, Math.max(0, data.current_step || 0));
  el.appendChild(svg("line", { x1: x(cur), x2: x(cur), y1: CHART.top, y2: CHART.height - CHART.bottom, class: "cursor-line", "data-role": "cursor" }));
  box.appendChild(el);
}

function renderValueAxis(el, min, max, y) {
  const right = CHART.width - CHART.right;
  for (let i = 0; i <= CHART.ticks; i++) {
    const v = min + ((max - min) * i) / CHART.ticks;
    el.appendChild(svg("line", { x1: CHART.left, x2: right, y1: y(v), y2: y(v), class: "grid-line" }));
    el.appendChild(svg("text", { x: CHART.left - 6, y: y(v) + 4, class: "axis-text", "text-anchor": "end" }, v.toFixed(2)));
  }
  if (min < 0 && max > 0) el.appendChild(svg("line", { x1: CHART.left, x2: right, y1: y(0), y2: y(0), class: "zero-line" }));
}

function renderHourAxis(el, n, dtHours, x) {
  const stepsPerHour = Math.round(1 / dtHours);
  for (let hour = 0; hour <= HOURS_PER_DAY; hour += CHART_HOUR_LABEL_STEP) {
    const i = Math.min(n - 1, hour * stepsPerHour);
    const label = String(hour).padStart(2, "0") + ":00";
    el.appendChild(svg("text", { x: x(i), y: CHART.height - 8, class: "axis-text", "text-anchor": "middle" }, label));
  }
}

export function moveChartCursor(stepOfDay) {
  const cursor = $("priceChart").querySelector('[data-role="cursor"]');
  if (!cursor || !state.pricesCount) return;
  const i = Math.min(state.pricesCount - 1, Math.max(0, stepOfDay));
  const xv = xOf(i, state.pricesCount).toFixed(1);
  cursor.setAttribute("x1", xv);
  cursor.setAttribute("x2", xv);
}
