import type { SimStatus } from '../types/api'

export function simStateLabel(status: SimStatus | null): { label: string; tone: 'ok' | 'warn' | 'off' | 'err' } {
  if (!status) return { label: 'necunoscut', tone: 'off' }
  if (!status.loaded) return { label: 'neîncărcată', tone: 'err' }
  if (status.running && status.paused) return { label: 'pauză', tone: 'warn' }
  if (status.running) return { label: 'rulează', tone: 'ok' }
  return { label: 'oprită', tone: 'off' }
}
