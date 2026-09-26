/* WebSocket către /api/admin/ws cu ping periodic și reconectare exponențială. */

import { WS_URL, WS_PING_MS, WS_BACKOFF_BASE_MS, WS_BACKOFF_MAX_MS } from "./constants.js";
import { T } from "./strings.js";
import { state } from "./state.js";
import { $, setText } from "./dom.js";
import { api } from "./api.js";

const socket = {
  ws: null,
  closing: false,   // închidere voită (logout / unload): nu reconecta
  retry: 0,
  retryTimer: null,
  pingTimer: null,
};

let handlers = { onStatus: () => {}, onStep: () => {} };
export function setSocketHandlers(h) {
  handlers = h;
}

function setConnection(ok, text) {
  $("connDot").className = "dot " + (ok ? "dot-on" : "dot-off");
  setText("connText", text);
}

export function closeSocket() {
  socket.closing = true;
  if (socket.retryTimer) clearTimeout(socket.retryTimer);
  if (socket.pingTimer) clearInterval(socket.pingTimer);
  socket.retryTimer = socket.pingTimer = null;
  if (socket.ws) {
    try { socket.ws.close(); } catch (e) { /* deja închis */ }
    socket.ws = null;
  }
  setConnection(false, T.wsDisconnected);
}

export function connectSocket() {
  if (!state.token) return;
  closeSocket();
  socket.closing = false;
  let ws;
  try {
    ws = new WebSocket(WS_URL + "?token=" + encodeURIComponent(state.token));
  } catch (e) {
    scheduleReconnect();
    return;
  }
  socket.ws = ws;
  setConnection(false, T.wsConnecting);
  ws.addEventListener("open", () => onOpen(ws));
  ws.addEventListener("message", onMessage);
  ws.addEventListener("close", () => onClose(ws));
  ws.addEventListener("error", () => { /* urmează close, care face reconectarea */ });
}

function onOpen(ws) {
  socket.retry = 0;
  setConnection(true, T.wsConnected);
  socket.pingTimer = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send("ping"); }, WS_PING_MS);
}

function onMessage(ev) {
  if (typeof ev.data !== "string" || ev.data === "pong") return;
  let msg;
  try { msg = JSON.parse(ev.data); } catch (e) { return; }
  if (!msg || typeof msg !== "object") return;
  if (msg.type === "connected") {
    handlers.onStatus(msg.status);
    if (msg.last) handlers.onStep(msg.last);
  } else if (msg.type === "step") {
    handlers.onStatus(msg.status);
    handlers.onStep(msg.data);
  } else if (msg.type === "status") {
    handlers.onStatus(msg.status);
  }
}

function onClose(ws) {
  if (socket.pingTimer) clearInterval(socket.pingTimer);
  socket.pingTimer = null;
  if (socket.ws === ws) socket.ws = null;
  if (!socket.closing) scheduleReconnect();
}

function scheduleReconnect() {
  if (socket.closing || !state.token) return;
  const delay = Math.min(WS_BACKOFF_MAX_MS, WS_BACKOFF_BASE_MS * Math.pow(2, socket.retry));
  socket.retry += 1;
  setConnection(false, T.wsReconnectIn(Math.round(delay / 1000)));
  socket.retryTimer = setTimeout(async () => {
    socket.retryTimer = null;
    // verifică întâi că token-ul e încă valid (altfel api() face logout)
    try { await api("/api/auth/me"); } catch (e) { return; }
    connectSocket();
  }, delay);
}

// La închiderea paginii nu vrem reconectare.
export function abandonSocket() {
  socket.closing = true;
  if (socket.ws) socket.ws.close();
}
