import type { SimStatus } from '../types/api'

// the most steps /api/sim/history returns in one answer
export const HISTORY_MAX = 600

/** How many past steps to ask for so that the whole simulated day is covered, whatever the step length. */
export function historySteps(status: Pick<SimStatus, 'steps_per_day'>): number {
  const perDay = Math.round(status.steps_per_day)
  if (!Number.isFinite(perDay) || perDay < 1) return HISTORY_MAX
  return Math.min(HISTORY_MAX, perDay)
}

export function simStateLabel(status: SimStatus | null): { label: string; tone: 'ok' | 'warn' | 'off' | 'err' } {
  if (!status) return { label: 'necunoscut', tone: 'off' }
  if (!status.loaded) return { label: 'neîncărcată', tone: 'err' }
  if (status.running && status.paused) return { label: 'pauză', tone: 'warn' }
  if (status.running) return { label: 'rulează', tone: 'ok' }
  return { label: 'oprită', tone: 'off' }
}
