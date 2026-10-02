import type { HouseStep, StepTrade } from '../types/api'

// positive: the house gives energy away (export + P2P sales), negative: it takes energy in
export function netExchangeKw(h: Pick<HouseStep, 'imp_kw' | 'exp_kw' | 'p2p_in_kw' | 'p2p_out_kw'>): number {
  return h.exp_kw + h.p2p_out_kw - h.imp_kw - h.p2p_in_kw
}

export interface Flow {
  from: number
  to: number
  kwh: number
}

// several trades between the same pair in one step are drawn as one line
export function p2pFlows(trades: StepTrade[]): Flow[] {
  const byPair = new Map<string, Flow>()
  for (const t of trades) {
    if (t.status !== 'settled' || t.seller_house_id === t.buyer_house_id) continue
    const key = `${t.seller_house_id}-${t.buyer_house_id}`
    const flow = byPair.get(key) ?? { from: t.seller_house_id, to: t.buyer_house_id, kwh: 0 }
    flow.kwh += t.energy_kwh
    byPair.set(key, flow)
  }
  return [...byPair.values()]
}

export function batteryModules(capacityKwh: number): number {
  // one battery module stores 16 kWh
  return Math.round(capacityKwh / 16)
}

export function socColor(percent: number): string {
  if (percent < 20) return 'var(--red)'
  if (percent < 50) return 'var(--amber)'
  return 'var(--green)'
}
