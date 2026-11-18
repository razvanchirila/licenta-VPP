import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

function Broken(): never {
  throw new Error('boom')
}

describe('ErrorBoundary', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('shows its children while nothing fails', () => {
    render(
      <ErrorBoundary>
        <p>conținut</p>
      </ErrorBoundary>,
    )
    expect(screen.getByText('conținut')).toBeTruthy()
  })

  it('replaces a page that throws with a message and a reload button', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert').textContent).toContain('Pagina nu a putut fi afișată')
    expect(screen.getByRole('button', { name: 'Reîncarcă pagina' })).toBeTruthy()
  })

  it('tries again when the page changes', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const { rerender } = render(
      <ErrorBoundary resetKey="/case">
        <Broken />
      </ErrorBoundary>,
    )
    rerender(
      <ErrorBoundary resetKey="/cartier">
        <p>altă pagină</p>
      </ErrorBoundary>,
    )
    expect(screen.getByText('altă pagină')).toBeTruthy()
  })
})
