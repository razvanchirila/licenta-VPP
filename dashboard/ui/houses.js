import { T } from "../strings.js";
import { state } from "../state.js";
import { $, h, clear, fmt } from "../dom.js";
import { guarded } from "../api.js";

// Coloanele numerice ale rândului, în ordinea din <thead>.
const HOUSE_FIELDS = ["mode", "soc", "pv", "load", "imp", "exp", "p2p", "wallet"];

function houseRowValues(house, step) {
  const s = step || house.last_step || {};
  const p2p = s.p2p_in_kw !== undefined ? (s.p2p_in_kw || 0) - (s.p2p_out_kw || 0) : null;
  const soc = s.soc_percent ?? (house.battery ? house.battery.soc_percent : null);
  return {
    mode: s.mode || house.mode || "–",
    soc: house.has_battery ? fmt(soc, 1) : T.noBattery,
    pv: fmt(s.pv_kw),
    load: fmt(s.load_kw),
    imp: fmt(s.imp_kw),
    exp: fmt(s.exp_kw),
    p2p: p2p === null ? "–" : (p2p > 0 ? "+" : "") + fmt(p2p),
    wallet: fmt(house.wallet_balance_lei),
  };
}

function renderHouseRow(house, onSelect) {
  const values = houseRowValues(house);
  const open = () => guarded(() => onSelect(house.id));
  const row = h("tr", { dataset: { houseId: String(house.id) }, tabindex: "0", on: {
    click: open,
    keydown: (ev) => { if (ev.key === "Enter") open(); },
  } },
    h("td", null, house.name),
    h("td", { class: "muted" }, house.user || "–"),
    ...HOUSE_FIELDS.map((f) => h("td", { dataset: { field: f } }, values[f])),
  );
  if (state.selectedHouse && state.selectedHouse.id === house.id) row.classList.add("selected");
  return row;
}

export function renderHousesTable(houses, onSelect) {
  state.houses = new Map(houses.map((x) => [x.id, x]));
  const body = $("housesBody");
  clear(body);
  for (const house of houses) body.appendChild(renderHouseRow(house, onSelect));
}

function houseRow(id) {
  return $("housesBody").querySelector('tr[data-house-id="' + id + '"]');
}

export function updateHouseRows(step) {
  for (const s of step.houses || []) {
    const house = state.houses.get(s.id);
    const row = houseRow(s.id);
    if (!house || !row) continue;
    house.last_step = s;
    const values = houseRowValues(house, s);
    for (const cell of row.querySelectorAll("td[data-field]")) cell.textContent = values[cell.dataset.field];
  }
}

export function setHouseRowField(id, field, value) {
  const row = houseRow(id);
  const cell = row && row.querySelector('td[data-field="' + field + '"]');
  if (cell) cell.textContent = value;
}

export function selectRow(id) {
  for (const row of $("housesBody").querySelectorAll("tr")) {
    row.classList.toggle("selected", id !== null && row.dataset.houseId === String(id));
  }
}
