import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/endpoints'
import { AuthContext, type AuthContextValue } from '../hooks/useAuth'
import type { House, User } from '../types/api'
import { UsersPage } from './UsersPage'

vi.mock('../api/endpoints', () => ({
  api: { users: vi.fn(), houses: vi.fn(), createUser: vi.fn(), updateUser: vi.fn(), deleteUser: vi.fn() },
}))

const user = (id: string, username: string, houseId: number | null, isAdmin = false): User => ({
  user_id: id,
  username,
  house_id: houseId,
  house_name: houseId === null ? null : `Casa ${houseId}`,
  is_admin: isAdmin,
  created_at: '2026-10-05T10:00:00',
})

const USERS = [user('u-admin', 'admin', null, true), user('u-1', 'casa1', 1)]
const HOUSES = [1, 2, 3].map((id) => ({ id, name: `Casa ${id}` })) as House[]

function renderPage() {
  const auth = { user: USERS[0] } as AuthContextValue
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <AuthContext value={auth}>
        <UsersPage />
      </AuthContext>
    </QueryClientProvider>,
  )
}

const field = (label: string) => screen.getByLabelText(label) as HTMLInputElement

async function openEditor(username: string) {
  fireEvent.click(await screen.findByRole('button', { name: `Editează utilizatorul ${username}` }))
  return within(screen.getByRole('dialog', { name: `Editează utilizatorul ${username}` }))
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.mocked(api.users).mockResolvedValue(USERS)
    vi.mocked(api.houses).mockResolvedValue(HOUSES)
    vi.mocked(api.createUser).mockResolvedValue(user('u-2', 'casa2', 2))
    vi.mocked(api.updateUser).mockResolvedValue(user('u-1', 'casa1', null))
  })
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('lists the users and does not let the admin delete the own account', async () => {
    renderPage()
    expect(await screen.findByText('casa1')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Șterge utilizatorul admin' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Șterge utilizatorul casa1' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('offers only the houses without a user', async () => {
    renderPage()
    await screen.findByRole('option', { name: 'Casa 2' })
    const options = screen.getAllByRole('option').map((o) => o.textContent)
    expect(options).toEqual(['Fără casă', 'Casa 2', 'Casa 3'])
  })

  it('shows the rules instead of sending a form that the server would refuse', async () => {
    renderPage()
    await screen.findByText('casa1')
    fireEvent.change(field('Nume de utilizator'), { target: { value: 'ștefan' } })
    fireEvent.change(field('Parolă'), { target: { value: 'ab' } })
    fireEvent.click(screen.getByRole('button', { name: 'Creează utilizatorul' }))

    expect(screen.getByText(/doar litere fără diacritice/)).toBeTruthy()
    expect(screen.getByText(/cel puțin 3 caractere/)).toBeTruthy()
    expect(field('Nume de utilizator').getAttribute('aria-invalid')).toBe('true')
    expect(api.createUser).not.toHaveBeenCalled()
  })

  it('sends a valid form and empties it afterwards', async () => {
    renderPage()
    await screen.findByRole('option', { name: 'Casa 2' })
    fireEvent.change(field('Nume de utilizator'), { target: { value: 'casa2' } })
    fireEvent.change(field('Parolă'), { target: { value: 'parola2' } })
    fireEvent.change(screen.getByLabelText('Casă'), { target: { value: '2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Creează utilizatorul' }))

    await waitFor(() => expect(api.createUser).toHaveBeenCalledOnce())
    expect(vi.mocked(api.createUser).mock.calls[0][0]).toEqual({
      username: 'casa2',
      password: 'parola2',
      house_id: 2,
      is_admin: false,
    })
    await waitFor(() => expect(field('Nume de utilizator').value).toBe(''))
  })

  it('edits a user with the free houses and the own house to choose from', async () => {
    renderPage()
    const dialog = await openEditor('casa1')
    await dialog.findByRole('option', { name: 'Casa 2' })
    expect(dialog.getAllByRole('option').map((o) => o.textContent)).toEqual(['Fără casă', 'Casa 1', 'Casa 2', 'Casa 3'])
    expect((dialog.getByLabelText('Casă') as HTMLSelectElement).value).toBe('1')
    expect((dialog.getByRole('button', { name: 'Salvează' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('sends house_id 0 when the house is taken away, and nothing else', async () => {
    renderPage()
    const dialog = await openEditor('casa1')
    await dialog.findByRole('option', { name: 'Casa 2' })
    fireEvent.change(dialog.getByLabelText('Casă'), { target: { value: '' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Salvează' }))

    await waitFor(() => expect(api.updateUser).toHaveBeenCalledOnce())
    expect(vi.mocked(api.updateUser).mock.calls[0]).toEqual(['u-1', { house_id: 0 }])
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /Editează/ })).toBeNull())
  })

  it('sends only the fields that were changed', async () => {
    renderPage()
    const dialog = await openEditor('casa1')
    fireEvent.click(dialog.getByRole('checkbox', { name: 'administrator' }))
    fireEvent.change(dialog.getByLabelText('Parolă nouă'), { target: { value: 'parolanoua' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Salvează' }))

    await waitFor(() => expect(api.updateUser).toHaveBeenCalledOnce())
    expect(vi.mocked(api.updateUser).mock.calls[0]).toEqual(['u-1', { is_admin: true, password: 'parolanoua' }])
  })

  it('does not send a new password that the server would refuse', async () => {
    renderPage()
    const dialog = await openEditor('casa1')
    fireEvent.change(dialog.getByLabelText('Parolă nouă'), { target: { value: 'ab' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Salvează' }))

    expect(dialog.getByText(/cel puțin 3 caractere/)).toBeTruthy()
    expect(api.updateUser).not.toHaveBeenCalled()
  })

  it('does not let the admin give up the own admin role', async () => {
    renderPage()
    const dialog = await openEditor('admin')
    const checkbox = dialog.getByRole('checkbox', { name: 'administrator' }) as HTMLInputElement
    expect(checkbox.checked).toBe(true)
    expect(checkbox.disabled).toBe(true)
    expect(dialog.getByText('Nu îți poți retrage propriul rol de administrator.')).toBeTruthy()
  })
})
