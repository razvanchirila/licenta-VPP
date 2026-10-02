import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { KpiCard } from './KpiCard'

describe('KpiCard', () => {
  afterEach(cleanup)

  it('shows the label, the value and the unit', () => {
    render(<KpiCard label="Producție PV" value="12,40" unit="kW" hint="putere instantanee" />)
    expect(screen.getByText('Producție PV')).toBeTruthy()
    expect(screen.getByText('12,40')).toBeTruthy()
    expect(screen.getByText('kW')).toBeTruthy()
    expect(screen.getByTitle('putere instantanee')).toBeTruthy()
  })

  it('renders without a unit', () => {
    const { container } = render(<KpiCard label="Controller" value="MPC" />)
    expect(container.textContent).toBe('ControllerMPC')
  })
})
