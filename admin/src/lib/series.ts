import type { DayPrices, StepResult } from '../types/api'
import { hourOf } from './format'

export interface PowerPoint {
  hour: number
  pv: number
  load: number
  import: number
  export: number
  p2p: number
}

export function powerSeries(day: StepResult[]): PowerPoint[] {
  return day.map((s) => ({
    hour: hourOf(s.sim_datetime),
    pv: s.community.pv_kw,
    load: s.community.load_kw,
    import: s.community.import_kw,
    export: s.community.export_kw,
    p2p: s.community.p2p_kw,
  }))
}

export interface PricePointByHour {
  hour: number
  import: number
  export: number
  p2p: number
}

export function priceSeries(prices: DayPrices | undefined): PricePointByHour[] {
  if (!prices) return []
  const points = prices.prices.map((p) => ({
    hour: hourOf(p.sim_timestamp),
    import: p.price_import,
    export: p.price_export,
    p2p: p.price_p2p,
  }))
  // the last interval is drawn up to 24:00 so the step line covers the whole day
  const last = points[points.length - 1]
  return last ? [...points, { ...last, hour: 24 }] : points
}

export const HOUR_TICKS = [0, 3, 6, 9, 12, 15, 18, 21, 24]
