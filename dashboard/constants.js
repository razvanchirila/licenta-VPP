export const API_BASE = location.origin;
export const WS_URL = API_BASE.replace(/^http/, "ws") + "/api/admin/ws";
export const TOKEN_KEY = "vpp_operator_token";

// Intervale (ms)
export const STATS_POLL_MS = 10000;
export const WS_PING_MS = 25000;         // ping pe WebSocket ca să nu cadă conexiunea
export const WS_BACKOFF_BASE_MS = 1000;
export const WS_BACKOFF_MAX_MS = 30000;
export const TOAST_MS = 4500;

// Limite de validare (aceleași ca în API)
export const TICK_SECONDS_MIN = 0.2;
export const TICK_SECONDS_MAX = 60;
export const DEVICE_POWER_W_MAX = 50000;
export const DEVICE_NAME_MAX = 100;
export const TRADES_SHOWN = 20;

// Graficul de prețuri (unități viewBox SVG)
export const CHART = { width: 640, height: 220, left: 44, right: 12, top: 12, bottom: 28, ticks: 4 };
export const CHART_HOUR_LABEL_STEP = 6;
export const DEFAULT_DT_HOURS = 0.25;
