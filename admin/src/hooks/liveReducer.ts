import type { SimStatus, StepResult, Trade } from '../types/api'

export const TRADES_KEPT = 20

export interface LiveState {
  status: SimStatus | null
  day: StepResult[]
  trades: Trade[]
}

export type LiveAction =
  | { type: 'status'; status: SimStatus }
  | { type: 'step'; step: StepResult; status?: SimStatus }
  | { type: 'history'; steps: StepResult[] }
  | { type: 'trades'; trades: Trade[] }
  | { type: 'reset' }

export const initialLiveState: LiveState = { status: null, day: [], trades: [] }

const dateOf = (step: StepResult) => step.sim_datetime.slice(0, 10)

// day holds the steps of one simulated day, oldest first, one entry per step number
export function mergeStep(day: StepResult[], step: StepResult): StepResult[] {
  const first = day[0]
  const last = day[day.length - 1]
  if (!first || !last) return [step]
  if (step.step < first.step) return [step]
  if (dateOf(step) !== dateOf(last)) return step.step > last.step ? [step] : day
  const index = day.findIndex((s) => s.step === step.step)
  if (index >= 0) return day.map((s, i) => (i === index ? step : s))
  return [...day, step].sort((a, b) => a.step - b.step)
}

const tradeKey = (t: Trade) => `${t.sim_timestamp}|${t.seller_house_id}|${t.buyer_house_id}`

export function mergeTrades(current: Trade[], incoming: Trade[]): Trade[] {
  const byKey = new Map<string, Trade>()
  for (const t of [...incoming, ...current]) if (!byKey.has(tradeKey(t))) byKey.set(tradeKey(t), t)
  return [...byKey.values()]
    .sort((a, b) => b.sim_timestamp.localeCompare(a.sim_timestamp))
    .slice(0, TRADES_KEPT)
}

export function stepTrades(step: StepResult): Trade[] {
  return step.trades.map((t) => ({ ...t, sim_timestamp: step.sim_datetime }))
}

export function liveReducer(state: LiveState, action: LiveAction): LiveState {
  switch (action.type) {
    case 'status':
      return { ...state, status: action.status }
    case 'step': {
      const restarted = state.day.length > 0 && action.step.step < state.day[0].step
      return {
        status: action.status ?? state.status,
        day: mergeStep(state.day, action.step),
        trades: mergeTrades(restarted ? [] : state.trades, stepTrades(action.step)),
      }
    }
    case 'history':
      return {
        ...state,
        day: [...action.steps, ...state.day].sort((a, b) => a.step - b.step).reduce(mergeStep, []),
      }
    case 'trades':
      return { ...state, trades: mergeTrades(state.trades, action.trades) }
    case 'reset':
      return { ...state, day: [], trades: [] }
  }
}
