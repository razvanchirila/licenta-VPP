import { setText, fmt, pct } from "../dom.js";

const KPI_IDS = ["kPv", "kLoad", "kImp", "kExp", "kP2p", "kSoc", "kPrice", "kPriceP2p"];

export function clearCommunity() {
  for (const id of KPI_IDS) setText(id, "–");
}

// Indicatorii (kW, %, lei/kWh) dintr-un StepResult.
export function renderCommunity(step) {
  const c = step.community || {};
  setText("kPv", fmt(c.pv_kw));
  setText("kLoad", fmt(c.load_kw));
  setText("kImp", fmt(c.import_kw));
  setText("kExp", fmt(c.export_kw));
  setText("kP2p", fmt(c.p2p_kw));
  setText("kSoc", fmt(c.soc_percent, 1));
  setText("kPrice", fmt(step.price && step.price.import, 3));
  setText("kPriceP2p", fmt(step.price && step.price.p2p, 3));
}

export function renderToday(stats) {
  const t = stats.today || {};
  setText("todayDate", t.date || "");
  setText("tPv", fmt(t.pv_kwh, 1));
  setText("tLoad", fmt(t.load_kwh, 1));
  setText("tImp", fmt(t.import_kwh, 1));
  setText("tExp", fmt(t.export_kwh, 1));
  setText("tP2p", fmt(t.p2p_kwh, 2));
  setText("tCost", fmt(t.cost_lei, 2));
  setText("tSc", pct(t.self_consumption));
  setText("tSs", pct(t.self_sufficiency));
  setText("tTrades", t.trades_settled ?? "–");
  setText("tTradesLei", fmt(t.trades_value_lei, 2));
}
