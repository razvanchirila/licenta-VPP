import { T } from "../strings.js";
import { state } from "../state.js";
import { $, h, clear } from "../dom.js";

const CONFIG_FIELDS = {
  controller: "cfgController", tick_seconds: "cfgTick", import_max_kw: "cfgImport", export_max_kw: "cfgExport",
  internal_line_kw: "cfgLine", p2p_price_factor: "cfgP2p", min_p2p_balance_lei: "cfgMinBal", seed: "cfgSeed",
};

export function fillConfig(cfg) {
  state.config = cfg;
  const sel = $("cfgController");
  clear(sel);
  for (const c of cfg.controllers || ["reguli", "mpc"]) sel.appendChild(h("option", { value: c }, c === "mpc" ? T.mpcOption : c));
  for (const [key, id] of Object.entries(CONFIG_FIELDS)) {
    if (cfg[key] !== undefined && cfg[key] !== null) $(id).value = String(cfg[key]);
  }
}

export function configChanges() {
  const body = {};
  for (const [key, id] of Object.entries(CONFIG_FIELDS)) {
    const raw = $(id).value;
    if (key === "controller") {
      if (raw !== state.config.controller) body[key] = raw;
      continue;
    }
    if (raw === "") continue;
    const num = key === "seed" ? parseInt(raw, 10) : parseFloat(raw);
    if (Number.isNaN(num)) throw new Error(T.invalidValue(key));
    if (num !== state.config[key]) body[key] = num;
  }
  return body;
}
