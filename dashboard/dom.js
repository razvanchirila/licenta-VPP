/* Utilitare DOM și de formatare. Toate datele intră în pagină prin textContent, nu prin innerHTML. */

import { TOAST_MS } from "./constants.js";

const SVG_NS = "http://www.w3.org/2000/svg";

export const $ = (id) => document.getElementById(id);

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined) continue;
      if (k === "class") el.className = v;
      else if (k === "dataset") Object.assign(el.dataset, v);
      else if (k === "on") for (const [ev, fn] of Object.entries(v)) el.addEventListener(ev, fn);
      else if (k in el && typeof v !== "string") el[k] = v;
      else el.setAttribute(k, v);
    }
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined) continue;
    el.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
  }
  return el;
}

// Varianta pentru SVG (namespace separat, atributele sunt mereu string).
export function svg(tag, attrs, text) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, String(v));
  if (text !== undefined) el.textContent = text;
  return el;
}

export function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

export function fmt(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "–";
  return Number(v).toFixed(digits);
}

export function pct(v) {
  return v === null || v === undefined ? "–" : Math.round(v * 100) + " %";
}

export function timeOf(iso) {
  if (!iso) return "–";
  const m = /T(\d{2}:\d{2})/.exec(iso);
  return m ? m[1] : iso;
}

export function toast(message, kind = "info") {
  const box = $("toasts");
  const el = h("div", { class: "toast toast-" + kind }, message);
  box.appendChild(el);
  setTimeout(() => el.remove(), TOAST_MS);
}
