import { describe, expect, it } from 'vitest'
import type { SimStatus, StepResult, StepTrade, Trade } from '../types/api'
import { initialLiveState, liveReducer, mergeStep, TRADES_KEPT } from './liveReducer'

function step(n: number, datetime: string, trades: StepTrade[] = [], pv = 1): StepResult {
  return {
    step: n,
    sim_datetime: datetime,
    dt_h: 0.25,
    controller: 'reguli',
    data_source: 'real',
    price: { import: 1, export: 0.5, p2p: 0.7 },
    community: {
      pv_kw: pv,
      load_kw: 1,
      device_kw: 1,
      shed_kw: 0,
      curtail_kw: 0,
      charge_kw: 0,
      discharge_kw: 0,
      import_kw: 0,
      export_kw: 0,
      p2p_kw: 0,
      soc_kwh: 0,
      soc_percent: 50,
    },
    houses: [],
    trades,
  }
}

const trade = (seller: number, buyer: number): StepTrade => ({
  seller_house_id: seller,
  buyer_house_id: buyer,
  energy_kwh: 0.1,
  price_lei_kwh: 1,
  total_value_lei: 0.1,
  status: 'settled',
})

const steps = (day: StepResult[]) => day.map((s) => s.step)

describe('mergeStep', () => {
  it('inserts steps of the same day in order', () => {
    const day = [step(1, '2026-10-05T00:00:00'), step(3, '2026-10-05T00:30:00')]
    expect(steps(mergeStep(day, step(2, '2026-10-05T00:15:00')))).toEqual([1, 2, 3])
  })

  it('replaces a step that arrives twice', () => {
    const day = [step(1, '2026-10-05T00:00:00')]
    const merged = mergeStep(day, step(1, '2026-10-05T00:00:00', [], 9))
    expect(merged).toHaveLength(1)
    expect(merged[0].community.pv_kw).toBe(9)
  })

  it('starts a new series when the simulated day changes', () => {
    const day = [step(95, '2026-10-05T23:45:00')]
    expect(steps(mergeStep(day, step(96, '2026-10-06T00:00:00')))).toEqual([96])
  })

  it('starts over after a reset (lower step number)', () => {
    const day = [step(40, '2026-10-05T10:00:00'), step(41, '2026-10-05T10:15:00')]
    expect(steps(mergeStep(day, step(1, '2026-10-05T00:00:00')))).toEqual([1])
  })
})

describe('liveReducer', () => {
  it('keeps only today from the history, together with live steps already received', () => {
    const live = liveReducer(initialLiveState, { type: 'step', step: step(97, '2026-10-06T00:15:00') })
    const state = liveReducer(live, {
      type: 'history',
      steps: [step(95, '2026-10-05T23:45:00'), step(96, '2026-10-06T00:00:00')],
    })
    expect(steps(state.day)).toEqual([96, 97])
  })

  it('puts the trades of a new step first and caps the list', () => {
    const old: Trade[] = Array.from({ length: TRADES_KEPT }, (_, i) => ({
      ...trade(1, 2),
      sim_timestamp: `2026-10-05T0${Math.floor(i / 10)}:${String(i % 10).padStart(2, '0')}:00`,
    }))
    let state = liveReducer(initialLiveState, { type: 'trades', trades: old })
    state = liveReducer(state, { type: 'step', step: step(50, '2026-10-05T12:00:00', [trade(6, 9)]) })
    expect(state.trades).toHaveLength(TRADES_KEPT)
    expect(state.trades[0]).toMatchObject({ seller_house_id: 6, buyer_house_id: 9, sim_timestamp: '2026-10-05T12:00:00' })
  })

  it('does not duplicate a trade delivered both by REST and by the socket', () => {
    let state = liveReducer(initialLiveState, { type: 'step', step: step(50, '2026-10-05T12:00:00', [trade(6, 9)]) })
    state = liveReducer(state, {
      type: 'trades',
      trades: [{ ...trade(6, 9), id: 7, sim_timestamp: '2026-10-05T12:00:00' }],
    })
    expect(state.trades).toHaveLength(1)
  })

  it('stores the status that comes with a step and clears everything on reset', () => {
    const status = { sim_time: '12:15' } as SimStatus
    let state = liveReducer(initialLiveState, {
      type: 'step',
      step: step(50, '2026-10-05T12:00:00', [trade(6, 9)]),
      status,
    })
    expect(state.status).toBe(status)
    state = liveReducer(state, { type: 'reset' })
    expect(state.day).toEqual([])
    expect(state.trades).toEqual([])
    expect(state.status).toBe(status)
  })
})
