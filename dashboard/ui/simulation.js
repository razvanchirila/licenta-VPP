import { T } from "../strings.js";
import { state } from "../state.js";
import { $, setText, fmt } from "../dom.js";

export function renderStatus(status) {
  if (!status) return;
  state.status = status;
  setText("simDate", status.sim_date || "–");
  setText("simTime", status.sim_time || "--:--");
  renderStatusBadge(status);
  renderStatusFields(status);
  renderSimButtons(status);
}

function renderStatusBadge(status) {
  const badge = $("simState");
  let label = T.simStopped, cls = "badge";
  if (status.running && status.paused) { label = T.simPaused; cls += " badge-warn"; }
  else if (status.running) { label = T.simRunning; cls += " badge-ok"; }
  if (!status.loaded) { label = T.simNotLoaded; cls = "badge badge-err"; }
  badge.textContent = label;
  badge.className = cls;
}

function renderStatusFields(status) {
  setText("stController", status.controller || "–");
  setText("stData", dataText(status));
  setText("stDt", status.dt_hours ? T.stepLabel(Math.round(status.dt_hours * 60), fmt(status.tick_seconds, 1)) : "–");
  setText("stSteps", status.total_steps ?? "–");
  setText("stStepOfDay", status.step_of_day !== undefined ? status.step_of_day + " / " + status.steps_per_day : "–");
  setText("stHouses", status.n_houses ?? "–");
  setText("stClients", status.websocket_clients ?? "–");
  const err = $("stError");
  err.textContent = status.last_error ? T.lastError + status.last_error : "";
  err.hidden = !status.last_error;
}

function dataText(status) {
  if (!status.data_source) return "–";
  return status.data_source === "real" ? T.dataReal(status.data_year) : T.dataSynthetic;
}

// Butoanele active depind de running/paused; viteza nu se suprascrie cât timp e editată.
function renderSimButtons(status) {
  $("btnStart").disabled = !!status.running;
  $("btnStop").disabled = !status.running;
  $("btnPause").disabled = !status.running || !!status.paused;
  $("btnResume").disabled = !status.running || !status.paused;
  const speed = $("speedInput");
  if (document.activeElement !== speed && status.tick_seconds !== undefined) speed.value = status.tick_seconds;
}
