import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ConfirmDialog } from './ConfirmDialog'

describe('ConfirmDialog', () => {
  afterEach(cleanup)

  it('is named by its title and described by its message', () => {
    const { container } = render(
      <ConfirmDialog
        open={false}
        title="Resetezi simularea?"
        message="Se șterg pașii."
        confirmLabel="Resetează"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    )
    const dialog = container.querySelector('dialog')!
    expect(dialog.getAttribute('aria-labelledby')).toBe(screen.getByText('Resetezi simularea?').id)
    expect(dialog.getAttribute('aria-describedby')).toBe(screen.getByText('Se șterg pașii.').id)
  })
})
