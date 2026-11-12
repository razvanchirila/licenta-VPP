import { describe, expect, it } from 'vitest'
import { HISTORY_MAX, historySteps } from './simState'

describe('historySteps', () => {
  it('asks for one simulated day of steps', () => {
    expect(historySteps({ steps_per_day: 288 })).toBe(288)
    expect(historySteps({ steps_per_day: 96 })).toBe(96)
    expect(historySteps({ steps_per_day: 24 })).toBe(24)
  })

  it('stays within what the server returns', () => {
    expect(historySteps({ steps_per_day: 1440 })).toBe(HISTORY_MAX)
  })

  it('asks for everything when the step length is not known', () => {
    expect(historySteps({ steps_per_day: 0 })).toBe(HISTORY_MAX)
    expect(historySteps({ steps_per_day: Number.NaN })).toBe(HISTORY_MAX)
  })
})
