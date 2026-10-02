import { describe, expect, it } from 'vitest'
import { formatHour, formatNumber, formatPercent, formatSigned, hourOf, scheduleText, timeOf } from './format'

describe('format', () => {
  it('uses the Romanian decimal comma and a dash for missing values', () => {
    expect(formatNumber(1234.5, 2)).toBe('1.234,50')
    expect(formatNumber(null)).toBe('–')
    expect(formatNumber(Number.NaN)).toBe('–')
  })

  it('never shows a negative zero', () => {
    expect(formatNumber(-0.001, 2)).toBe('0,00')
    expect(formatSigned(-0.001, 2)).toBe('0,00')
  })

  it('adds a plus sign only to positive values', () => {
    expect(formatSigned(1.5, 1)).toBe('+1,5')
    expect(formatSigned(-1.5, 1)).toBe('-1,5')
  })

  it('formats fractions as percentages', () => {
    expect(formatPercent(0.233)).toBe('23 %')
    expect(formatPercent(null)).toBe('–')
  })

  it('reads the time of day from simulated timestamps', () => {
    expect(timeOf('2026-10-05T04:45:00')).toBe('04:45')
    expect(hourOf('2026-10-05T04:45:00')).toBe(4.75)
    expect(formatHour(4.75)).toBe('04:45')
    expect(formatHour(24)).toBe('00:00')
  })

  it('describes device schedules', () => {
    expect(scheduleText(null)).toBe('manual, cât e pornit')
    expect(
      scheduleText({
        mode: 'zilnic',
        hours_per_day: 5,
        cycles_per_week: 0,
        cycle_minutes: 0,
        interval: '17-23',
        season: 'tot_anul',
      }),
    ).toBe('5 h/zi, între 17-23')
  })
})
