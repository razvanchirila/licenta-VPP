import { DEVICE_POWER_W_MAX, DEVICE_NAME_MAX } from "../constants.js";
import { T } from "../strings.js";
import { state } from "../state.js";
import { $, h, clear, setText, fmt, toast } from "../dom.js";
import { api, guarded } from "../api.js";
import { selectRow, setHouseRowField } from "./houses.js";

export async function openHouse(id) {
  const house = await api("/api/houses/" + id);
  state.houses.set(house.id, house);
  state.selectedHouse = house;
  state.editingDevice = null;
  selectRow(house.id);
  renderHouse(house);
  $("houseCard").hidden = false;
}

export function closeHouse() {
  state.selectedHouse = null;
  state.editingDevice = null;
  selectRow(null);
  $("houseCard").hidden = true;
}

function renderHouse(house) {
  setText("houseTitle", house.name + (house.user ? " (" + house.user + ")" : ""));
  const body = $("houseBody");
  clear(body);
  body.appendChild(h("div", { class: "house-grid" }, renderHouseSummary(house), renderBattery(house)));
  body.appendChild(h("h3", null, T.devicesHeading(house.device_count)));
  body.appendChild(renderDeviceTable(house));
  if (!house.devices.length) body.appendChild(h("p", { class: "muted" }, T.noDevices));
  body.appendChild(h("div", { id: "deviceEdit" }));
  if (state.editingDevice) openDeviceEdit(state.editingDevice);
}

function renderHouseSummary(house) {
  const tr = house.trading;
  const modeBtn = (mode) => h("button", {
    class: "btn btn-sm" + (house.mode === mode ? " active" : ""), type: "button",
    on: { click: () => guarded(() => setMode(house.id, mode)) },
  }, mode);
  return h("div", null,
    h("h3", null, T.modeHeading),
    h("div", { class: "actions" }, modeBtn("Eco"), modeBtn("Profit")),
    h("dl", { class: "kv" },
      h("dt", null, T.pvCapacity), h("dd", null, house.has_pv ? fmt(house.pv_capacity_kw, 1) + " kW" : T.noPv),
      h("dt", null, T.loadCritNoncrit), h("dd", null, fmt(house.L_crit_kw) + " / " + fmt(house.L_noncrit_kw) + " kW"),
      h("dt", null, T.walletBalance), h("dd", null, fmt(house.wallet_balance_lei) + " lei"),
      h("dt", null, T.p2pLabel), h("dd", null, tr ? T.p2pPrefs(tr.selling_enabled, tr.buying_enabled) : "–"),
    ),
  );
}

// Coloana dreaptă: bateria; valorile marcate data-live se actualizează la fiecare pas.
function renderBattery(house) {
  const b = house.battery;
  const step = house.last_step || {};
  if (!b) return h("div", null, h("h3", null, T.batteryHeading), h("p", { class: "muted" }, T.houseNoBattery));
  return h("div", null,
    h("h3", null, T.batteryHeading),
    h("dl", { class: "kv" },
      h("dt", null, T.soc), h("dd", { dataset: { live: "soc" } }, socText(step.soc_percent ?? b.soc_percent, step.soc_kwh ?? b.soc_kwh)),
      h("dt", null, T.capacity), h("dd", null, T.capacityValue(fmt(b.capacity_kwh, 1), fmt(b.soc_min_kwh, 1))),
      h("dt", null, T.chargePower), h("dd", null, fmt(b.p_ch_max_kw, 1) + " / " + fmt(b.p_dis_max_kw, 1) + " kW"),
      h("dt", null, T.vppReserve), h("dd", null, fmt(b.vpp_reserve_kwh, 2) + " kWh"),
      h("dt", null, T.chargingNow), h("dd", { dataset: { live: "batt" } }, chargeText(step.ch_kw, step.dis_kw)),
    ),
  );
}

function socText(percent, kwh) {
  return fmt(percent, 1) + " % (" + fmt(kwh, 2) + " kWh)";
}

function chargeText(chKw, disKw) {
  return fmt(chKw) + " / " + fmt(disKw) + " kW";
}

function renderDeviceTable(house) {
  const head = h("tr", null, T.deviceCols.map((label) => h("th", null, label)));
  const rows = house.devices.map((d) => renderDeviceRow(house, d));
  return h("div", { class: "table-wrap" }, h("table", { class: "table small-table" },
    h("thead", null, head),
    h("tbody", null, rows),
  ));
}

function renderDeviceRow(house, d) {
  const locked = d.critical && d.status_on;
  return h("tr", { dataset: { deviceId: String(d.id) } },
    h("td", null, d.name),
    h("td", null, scheduleText(d.schedule)),
    h("td", null, fmt(d.power_w, 0) + " W"),
    h("td", null, fmt(d.current_power_kw, 2) + " kW"),
    h("td", null, d.critical ? T.critical : T.nonCritical),
    h("td", null, h("span", { class: "pill " + (d.status_on ? "pill-on" : "pill-off") }, d.status_on ? T.on : T.off)),
    h("td", null, fmt(d.accumulated_energy_kwh, 3) + " kWh"),
    h("td", { class: "actions-cell" },
      h("button", { class: "btn btn-sm", type: "button", disabled: locked, title: locked ? T.criticalDevice : null,
        on: { click: () => guarded(() => toggleDevice(house.id, d.id)) } }, d.status_on ? T.turnOff : T.turnOn),
      h("button", { class: "btn btn-sm", type: "button", on: { click: () => openDeviceEdit(d) } }, T.edit),
    ),
  );
}

function scheduleText(sc) {
  if (!sc) return T.scheduleManual;
  const num = (v) => String(Math.round(v * 10) / 10);
  switch (sc.mode) {
    case "zilnic": return T.scheduleDaily(num(sc.hours_per_day), sc.interval);
    case "ciclic": return T.scheduleCyclic(num(sc.cycles_per_week), num(sc.cycle_minutes), sc.interval);
    case "termic": return T.scheduleThermal(T.seasons[sc.season] || sc.season);
    default: return T.scheduleContinuous;
  }
}

export function updateHouseLive(step) {
  const house = state.selectedHouse;
  if (!house) return;
  const s = (step.houses || []).find((x) => x.id === house.id);
  if (!s) return;
  const soc = $("houseBody").querySelector('[data-live="soc"]');
  if (soc) soc.textContent = socText(s.soc_percent, s.soc_kwh);
  const batt = $("houseBody").querySelector('[data-live="batt"]');
  if (batt) batt.textContent = chargeText(s.ch_kw, s.dis_kw);
}

async function setMode(houseId, mode) {
  const res = await api("/api/houses/" + houseId + "/mode", { method: "POST", body: { mode } });
  toast(res.message, "ok");
  await openHouse(houseId);
  setHouseRowField(houseId, "mode", res.mode);
}

async function toggleDevice(houseId, deviceId) {
  const d = await api("/api/houses/" + houseId + "/devices/" + deviceId + "/toggle", { method: "POST" });
  toast(d.name + ": " + (d.status_on ? T.on : T.off), "ok");
  await openHouse(houseId);
}

function openDeviceEdit(device) {
  state.editingDevice = device;
  const box = $("deviceEdit");
  if (!box) return;
  clear(box);
  const inputs = {
    name: h("input", { type: "text", maxlength: String(DEVICE_NAME_MAX), required: true, value: device.name }),
    power: h("input", { type: "number", min: "1", max: String(DEVICE_POWER_W_MAX), step: "1", required: true, value: String(device.power_w) }),
    critical: h("input", { type: "checkbox", checked: !!device.critical }),
    on: h("input", { type: "checkbox", checked: !!device.status_on }),
  };
  const cancel = () => { state.editingDevice = null; clear(box); };
  const form = h("form", { class: "device-form", on: { submit: (ev) => {
    ev.preventDefault();
    guarded(() => saveDevice(device, inputs));
  } } },
    h("h4", null, T.editTitle(device.name)),
    h("label", null, T.fieldName, inputs.name),
    h("label", null, T.fieldPower, inputs.power),
    h("label", { class: "check" }, inputs.critical, " " + T.critical),
    h("label", { class: "check" }, inputs.on, " " + T.on),
    h("div", { class: "actions" },
      h("button", { type: "submit", class: "btn btn-primary btn-sm" }, T.save),
      h("button", { type: "button", class: "btn btn-sm", on: { click: cancel } }, T.cancel),
    ),
  );
  box.appendChild(form);
  inputs.name.focus();
}

function deviceChanges(device, inputs) {
  const body = {};
  const name = inputs.name.value.trim();
  if (name !== device.name) body.name = name;
  const power = parseFloat(inputs.power.value);
  if (power !== device.power_w) body.power_w = power;
  if (inputs.critical.checked !== device.critical) body.critical = inputs.critical.checked;
  if (inputs.on.checked !== device.status_on) body.status_on = inputs.on.checked;
  return body;
}

async function saveDevice(device, inputs) {
  const body = deviceChanges(device, inputs);
  if (!Object.keys(body).length) { toast(T.nothingToChange); return; }
  await api("/api/houses/" + device.house_id + "/devices/" + device.id, { method: "PUT", body });
  toast(T.deviceSaved, "ok");
  state.editingDevice = null;
  await openHouse(device.house_id);
}
