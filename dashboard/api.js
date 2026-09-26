/* Apeluri HTTP către backend și gestiunea token-ului de sesiune. */

import { API_BASE, TOKEN_KEY } from "./constants.js";
import { T } from "./strings.js";
import { state } from "./state.js";
import { toast } from "./dom.js";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Ce se întâmplă la 401: setat de app.js (delogare + ecran de login).
let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

// Mesaj lizibil dintr-un răspuns de eroare FastAPI ({detail: string | [{loc, msg}]}).
function errorText(body, fallback) {
  if (!body) return fallback;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((e) => (e.loc ? e.loc.slice(1).join(".") + ": " : "") + e.msg).join("; ");
  }
  return fallback;
}

async function parseJson(res) {
  const text = await res.text();
  if (!text) return null;
  try { return JSON.parse(text); } catch (e) { return null; }
}

export async function api(path, { method = "GET", body = undefined, auth = true } = {}) {
  const headers = { Accept: "application/json" };
  if (auth && state.token) headers.Authorization = "Bearer " + state.token;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(API_BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch (e) {
    throw new ApiError(0, T.serverDown);
  }
  const data = await parseJson(res);
  if (res.status === 401 && auth) {
    onUnauthorized(T.sessionExpiredLogin);
    throw new ApiError(401, T.sessionExpired);
  }
  if (!res.ok) {
    const fallback = res.status === 403 ? T.forbidden : T.errorPrefix + res.status;
    throw new ApiError(res.status, errorText(data, fallback));
  }
  return data;
}

// Rulează o acțiune de UI și arată eroarea ca toast (401 e deja tratat de api()).
export async function guarded(fn) {
  try {
    await fn();
  } catch (e) {
    if (!(e instanceof ApiError && e.status === 401)) toast(e.message || String(e), "error");
  }
}

// ---- token de sesiune (sessionStorage poate lipsi, de ex. în mod privat)
export function saveToken(token) {
  state.token = token;
  try { sessionStorage.setItem(TOKEN_KEY, token); } catch (e) { /* stocare indisponibilă */ }
}

export function loadSavedToken() {
  try { return sessionStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
}

export function clearToken() {
  state.token = null;
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (e) { /* stocare indisponibilă */ }
}

export function login(username, password) {
  return api("/api/auth/login", { method: "POST", body: { username, password }, auth: false });
}

export function fetchMe() {
  return api("/api/auth/me");
}
