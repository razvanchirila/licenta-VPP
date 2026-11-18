import { describe, expect, it } from 'vitest'
import { formatHour, formatNumber, formatPercent, formatSigned, hourOf, minutesText, scheduleText, timeOf } from './format'

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

  it('writes the step length in minutes, with "de" from 20 up', () => {
    expect(minutesText(5 / 60)).toBe('5 minute')
    expect(minutesText(0.25)).toBe('15 minute')
    expect(minutesText(0.5)).toBe('30 de minute')
    expect(minutesText(1)).toBe('60 de minute')
    expect(minutesText(1 / 60)).toBe('1 minut')
    expect(minutesText(undefined)).toBe('–')
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
    expect(scheduleText({ mode: 'interval', text: '18-23; 10-14 weekend' })).toBe('18-23; 10-14 weekend')
  })
})
