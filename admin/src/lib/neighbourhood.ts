import type { HouseSpec } from '../types/api'

const INSULATION: Record<string, string> = { noua: 'nouă', medie: 'medie', veche: 'veche' }

export function insulationLabel(value: string): string {
  return INSULATION[value] ?? value
}

export function heatingLabel(value: string): string {
  return value === 'gaz' ? 'gaz sau lemne' : value
}

/** Adds or removes a device, keeping the catalog order. */
export function toggleDevice(spec: HouseSpec, name: string, catalogOrder: string[]): HouseSpec {
  const owned = new Set(spec.devices)
  if (owned.has(name)) owned.delete(name)
  else owned.add(name)
  return { ...spec, devices: catalogOrder.filter((n) => owned.has(n)) }
}

export function sameSpec(a: HouseSpec, b: HouseSpec): boolean {
  return (
    a.description === b.description &&
    a.people === b.people &&
    a.home_daytime === b.home_daytime &&
    a.heating === b.heating &&
    a.insulation === b.insulation &&
    [...a.devices].sort().join(',') === [...b.devices].sort().join(',')
  )
}
