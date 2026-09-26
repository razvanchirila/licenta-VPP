import { TRADES_SHOWN } from "../constants.js";
import { T } from "../strings.js";
import { state } from "../state.js";
import { $, h, clear, fmt, timeOf } from "../dom.js";

function houseName(id) {
  const house = state.houses.get(id);
  return house ? house.name : T.houseFallback(id);
}

function renderTradeRow(t) {
  return h("tr", { class: t.status === "rejected" ? "rejected" : null },
    h("td", null, timeOf(t.sim_timestamp)),
    h("td", null, houseName(t.seller_house_id)),
    h("td", null, houseName(t.buyer_house_id)),
    h("td", null, fmt(t.energy_kwh, 3)),
    h("td", null, fmt(t.price_lei_kwh, 3)),
    h("td", null, fmt(t.total_value_lei, 3)),
    h("td", null, t.status === "settled" ? T.settled : T.rejected),
  );
}

export function renderTrades() {
  const body = $("tradesBody");
  clear(body);
  if (!state.trades.length) {
    body.appendChild(h("tr", null, h("td", { colspan: "7", class: "muted" }, T.noTrades)));
    return;
  }
  for (const t of state.trades.slice(0, TRADES_SHOWN)) body.appendChild(renderTradeRow(t));
}

export function addStepTrades(step) {
  const items = (step.trades || []).map((t) => ({ ...t, sim_timestamp: step.sim_datetime }));
  if (!items.length) return;
  state.trades = items.concat(state.trades).slice(0, TRADES_SHOWN);
  renderTrades();
}
