/* Punct de intrare. Vanilla JS, fără build; modulele sunt în api.js, ws.js și ui/. */

import { STATS_POLL_MS, TICK_SECONDS_MIN, TICK_SECONDS_MAX, TRADES_SHOWN } from "./constants.js";
import { T } from "./strings.js";
import { state } from "./state.js";
import { $, setText, toast } from "./dom.js";
import { api, ApiError, guarded, login, fetchMe, saveToken, loadSavedToken, clearToken, setUnauthorizedHandler } from "./api.js";
import { connectSocket, closeSocket, abandonSocket, setSocketHandlers } from "./ws.js";
import { renderStatus } from "./ui/simulation.js";
import { renderCommunity, clearCommunity, renderToday } from "./ui/community.js";
import { renderHousesTable, updateHouseRows } from "./ui/houses.js";
import { openHouse, closeHouse, updateHouseLive } from "./ui/house.js";
import { fillConfig, configChanges } from "./ui/config.js";
import { renderPriceChart, moveChartCursor } from "./ui/prices.js";
import { renderTrades, addStepTrades } from "./ui/trades.js";

let statsTimer = null;

async function loadStatus() {
  applyStatus(await api("/api/sim/status"));
}

async function loadHouses() {
  renderHousesTable(await api("/api/houses"), openHouse);
}

async function loadConfig() {
  fillConfig(await api("/api/config"));
}

async function loadStats() {
  const stats = await api("/api/vpp/stats");
  renderToday(stats);
  if (stats.last_step) renderCommunity(stats.last_step);
}

async function loadTrades() {
  const res = await api("/api/trading/recent?limit=" + TRADES_SHOWN);
  state.trades = res.transactions || [];
  renderTrades();
}

async function loadPrices() {
  const data = await api("/api/sim/prices");
  state.pricesDate = data.date;
  state.pricesCount = (data.prices || []).length;
  renderPriceChart(data);
}

function applyStatus(status) {
  if (!status) return;
  renderStatus(status);
  // graficul e al unei zile; când ziua simulată se schimbă, îl reîncărcăm
  if (state.pricesDate && status.sim_date && status.sim_date !== state.pricesDate) guarded(loadPrices);
}

function applyStep(step) {
  if (!step) return;
  renderCommunity(step);
  updateHouseRows(step);
  updateHouseLive(step);
  addStepTrades(step);
  // status.step_of_day este indexul pasului următor; pasul tocmai rulat e cel dinainte
  const spd = state.status && state.status.steps_per_day;
  if (spd) moveChartCursor(((state.status.step_of_day - 1) % spd + spd) % spd);
}

function showLogin(message) {
  $("app").hidden = true;
  $("login").hidden = false;
  const err = $("loginError");
  err.textContent = message || "";
  err.hidden = !message;
  $("loginUser").focus();
}

function showApp() {
  $("login").hidden = true;
  $("app").hidden = false;
}

function logout(message) {
  clearToken();
  state.user = null;
  closeSocket();
  if (statsTimer) clearInterval(statsTimer);
  statsTimer = null;
  showLogin(message);
}

async function onLoginSubmit(ev) {
  ev.preventDefault();
  const btn = $("loginBtn");
  btn.disabled = true;
  try {
    const res = await login($("loginUser").value.trim(), $("loginPass").value);
    if (!res.is_admin) {
      showLogin(T.notAdmin);
      return;
    }
    saveToken(res.access_token);
    $("loginPass").value = "";
    await enterApp();
  } catch (e) {
    showLogin(e.status === 401 ? T.badCredentials : e.message);
  } finally {
    btn.disabled = false;
  }
}

async function enterApp() {
  const me = await fetchMe();
  if (!me.is_admin) {
    logout(T.notAdmin);
    return;
  }
  state.user = me;
  setText("userName", me.username);
  showApp();
  await Promise.all([guarded(loadStatus), guarded(loadHouses), guarded(loadConfig), guarded(loadStats), guarded(loadTrades)]);
  await guarded(loadPrices);
  if (statsTimer) clearInterval(statsTimer);
  statsTimer = setInterval(() => guarded(loadStats), STATS_POLL_MS);
  connectSocket();
}

async function simAction(path) {
  const res = await api(path, { method: "POST" });
  if (res && res.status) applyStatus(res.status);
  if (res && res.message) toast(res.message, "ok");
}

async function simStep() {
  const step = await api("/api/sim/step", { method: "POST" });
  await loadStatus();
  applyStep(step);
  await loadStats();
}

async function simReset() {
  if (!window.confirm(T.confirmReset)) return;
  await simAction("/api/sim/reset");
  state.trades = [];
  renderTrades();
  await Promise.all([loadHouses(), loadStats(), loadPrices()]);
  if (state.selectedHouse) await openHouse(state.selectedHouse.id);
  clearCommunity();
}

async function applySpeed() {
  const value = parseFloat($("speedInput").value);
  if (!(value >= TICK_SECONDS_MIN && value <= TICK_SECONDS_MAX)) throw new Error(T.speedRange);
  const res = await api("/api/sim/speed", { method: "POST", body: { tick_seconds: value } });
  toast(res.message, "ok");
  await Promise.all([loadStatus(), loadConfig()]);
}

function bindSimControls() {
  $("btnStart").addEventListener("click", () => guarded(() => simAction("/api/sim/start")));
  $("btnStop").addEventListener("click", () => guarded(() => simAction("/api/sim/stop")));
  $("btnPause").addEventListener("click", () => guarded(() => simAction("/api/sim/pause")));
  $("btnResume").addEventListener("click", () => guarded(() => simAction("/api/sim/resume")));
  $("btnStep").addEventListener("click", () => guarded(simStep));
  $("btnReset").addEventListener("click", () => guarded(simReset));
  $("btnSpeed").addEventListener("click", () => guarded(applySpeed));
}

async function saveConfig(ev) {
  ev.preventDefault();
  await guarded(async () => {
    const body = configChanges();
    if (!Object.keys(body).length) { toast(T.nothingToChange); return; }
    const res = await api("/api/config", { method: "PUT", body });
    fillConfig(res.config);
    toast(res.message, "ok");
    await loadStatus();
  });
}

async function resetConfig() {
  await guarded(async () => {
    const res = await api("/api/config/reset", { method: "POST" });
    fillConfig(res.config);
    toast(res.message, "ok");
    await loadStatus();
  });
}

function init() {
  setUnauthorizedHandler(logout);
  setSocketHandlers({ onStatus: applyStatus, onStep: applyStep });
  $("loginForm").addEventListener("submit", onLoginSubmit);
  $("logoutBtn").addEventListener("click", () => logout());
  $("houseClose").addEventListener("click", closeHouse);
  $("configForm").addEventListener("submit", saveConfig);
  $("cfgReset").addEventListener("click", resetConfig);
  bindSimControls();
  window.addEventListener("beforeunload", abandonSocket);

  const saved = loadSavedToken();
  if (saved) {
    state.token = saved;
    enterApp().catch((e) => { if (!(e instanceof ApiError && e.status === 401)) logout(e.message); });
  } else {
    showLogin();
  }
}

document.addEventListener("DOMContentLoaded", init);
