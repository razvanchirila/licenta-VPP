import type { DeviceSchedule } from '../types/api'

const DASH = '–'
const formatters = new Map<number, Intl.NumberFormat>()

function formatter(digits: number): Intl.NumberFormat {
  let f = formatters.get(digits)
  if (!f) {
    f = new Intl.NumberFormat('ro-RO', { minimumFractionDigits: digits, maximumFractionDigits: digits })
    formatters.set(digits, f)
  }
  return f
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH
  // avoids "-0,00" for tiny negative values
  const rounded = Math.round(value * 10 ** digits) / 10 ** digits
  return formatter(digits).format(rounded === 0 ? 0 : rounded)
}

export function formatSigned(value: number | null | undefined, digits = 2): string {
  const text = formatNumber(value, digits)
  return value !== null && value !== undefined && Math.round(value * 10 ** digits) > 0 ? `+${text}` : text
}

export function formatPercent(fraction: number | null | undefined, digits = 0): string {
  if (fraction === null || fraction === undefined) return DASH
  return `${formatNumber(fraction * 100, digits)} %`
}

export function timeOf(iso: string | null | undefined): string {
  const match = iso ? /T(\d{2}:\d{2})/.exec(iso) : null
  return match ? match[1] : DASH
}

export function hourOf(iso: string): number {
  const match = /T(\d{2}):(\d{2})/.exec(iso)
  return match ? Number(match[1]) + Number(match[2]) / 60 : 0
}

export function formatDate(isoDate: string | null | undefined): string {
  const match = isoDate ? /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate) : null
  return match ? `${match[3]}.${match[2]}.${match[1]}` : DASH
}

export function formatHour(hour: number): string {
  const h = Math.floor(hour) % 24
  const m = Math.round((hour - Math.floor(hour)) * 60)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

export function scheduleText(schedule: DeviceSchedule | null): string {
  return schedule ? schedule.text : 'manual, cât e pornit'
}

export function dataSourceText(source: string | undefined, year: number | undefined): string {
  if (!source) return DASH
  return source === 'real' ? `reale ${year ?? ''}`.trim() : 'sintetice'
}
