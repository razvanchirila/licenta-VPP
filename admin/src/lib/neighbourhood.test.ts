import { describe, expect, it } from 'vitest'
import type { HouseSpec } from '../types/api'
import { heatingLabel, sameSpec, toggleDevice } from './neighbourhood'

const spec: HouseSpec = {
  id: 1,
  description: 'pensionar',
  people: 1,
  home_daytime: true,
  heating: 'gaz',
  insulation: 'veche',
  devices: ['microunde', 'aspirator'],
}
const order = ['congelator', 'microunde', 'masina de spalat', 'aspirator']

describe('neighbourhood editor', () => {
  it('toggles a device and keeps the catalog order', () => {
    expect(toggleDevice(spec, 'congelator', order).devices).toEqual(['congelator', 'microunde', 'aspirator'])
    expect(toggleDevice(spec, 'microunde', order).devices).toEqual(['aspirator'])
  })

  it('compares specs regardless of device order', () => {
    expect(sameSpec(spec, { ...spec, devices: ['aspirator', 'microunde'] })).toBe(true)
    expect(sameSpec(spec, { ...spec, people: 2 })).toBe(false)
  })

  it('names gas heating for people', () => {
    expect(heatingLabel('gaz')).toBe('gaz sau lemne')
    expect(heatingLabel('pompa de caldura')).toBe('pompa de caldura')
  })
})
