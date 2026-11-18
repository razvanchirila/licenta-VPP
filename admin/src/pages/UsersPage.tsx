import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { useEffect, useEffectEvent, useId, useRef, useState, type FormEvent } from 'react'
import { api } from '../api/endpoints'
import { Card } from '../components/Card'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { Spinner } from '../components/Spinner'
import tableStyles from '../components/Table.module.css'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { formatDate } from '../lib/format'
import {
  editOf,
  emptyUserDraft,
  freeHouses,
  passwordError,
  toNewUser,
  userChanges,
  validateUser,
  type UserDraft,
  type UserEdit,
} from '../lib/users'
import type { House, User, UserUpdate } from '../types/api'
import styles from './UsersPage.module.css'

function NewUserForm({ houses, onCreated }: { houses: House[] | undefined; onCreated: () => void }) {
  const toast = useToast()
  const id = useId()
  const usernameError = `${id}-username-error`
  const passwordError = `${id}-password-error`
  const [draft, setDraft] = useState<UserDraft>(emptyUserDraft)
  const [submitted, setSubmitted] = useState(false)
  const errors = submitted ? validateUser(draft) : {}

  const create = useMutation({
    mutationFn: api.createUser,
    onSuccess: (user) => {
      toast(`Utilizatorul ${user.username} a fost creat`, 'ok')
      setDraft(emptyUserDraft)
      setSubmitted(false)
      onCreated()
    },
    onError: (error) => toast(error.message, 'error'),
  })
  const set = <K extends keyof UserDraft>(key: K, value: UserDraft[K]) => setDraft({ ...draft, [key]: value })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    if (Object.keys(validateUser(draft)).length === 0) create.mutate(toNewUser(draft))
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <div className={styles.fields}>
        <div className={styles.field}>
          <label htmlFor={`${id}-username`}>Nume de utilizator</label>
          <input
            id={`${id}-username`}
            className="input"
            name="username"
            autoComplete="off"
            maxLength={50}
            value={draft.username}
            onChange={(e) => set('username', e.target.value)}
            aria-invalid={Boolean(errors.username)}
            aria-describedby={errors.username ? usernameError : undefined}
          />
          {errors.username && (
            <span id={usernameError} className={styles.error}>
              {errors.username}
            </span>
          )}
        </div>
        <div className={styles.field}>
          <label htmlFor={`${id}-password`}>Parolă</label>
          <input
            id={`${id}-password`}
            className="input"
            name="password"
            type="password"
            autoComplete="new-password"
            value={draft.password}
            onChange={(e) => set('password', e.target.value)}
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? passwordError : undefined}
          />
          {errors.password && (
            <span id={passwordError} className={styles.error}>
              {errors.password}
            </span>
          )}
        </div>
        <label className={styles.field}>
          <span>Casă</span>
          <select className="input" value={draft.houseId} disabled={!houses} onChange={(e) => set('houseId', e.target.value)}>
            <option value="">Fără casă</option>
            {houses?.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
        </label>
        <div className={styles.field}>
          <span>Rol</span>
          <label className={styles.check}>
            <input type="checkbox" checked={draft.isAdmin} onChange={(e) => set('isAdmin', e.target.checked)} />
            administrator
          </label>
        </div>
      </div>
      <div className={styles.actions}>
        <button type="submit" className="btn btn-primary" disabled={create.isPending}>
          {create.isPending ? 'Se creează…' : 'Creează utilizatorul'}
        </button>
        <span className="muted">În listă apar doar casele care nu au încă un utilizator.</span>
      </div>
    </form>
  )
}

interface EditUserDialogProps {
  user: User
  self: boolean
  houses: House[] | undefined
  onClose: () => void
  onSaved: () => void
}

function EditUserDialog({ user, self, houses, onClose, onSaved }: EditUserDialogProps) {
  const toast = useToast()
  const id = useId()
  const firstField = useRef<HTMLSelectElement>(null)
  const [edit, setEdit] = useState<UserEdit>(() => editOf(user))
  const [submitted, setSubmitted] = useState(false)
  const changes = userChanges(user, edit)
  const dirty = Object.keys(changes).length > 0
  const passwordProblem = edit.password === '' ? undefined : passwordError(edit.password)

  const save = useMutation({
    mutationFn: (body: UserUpdate) => api.updateUser(user.user_id, body),
    onSuccess: (saved) => {
      toast(`Utilizatorul ${saved.username} a fost actualizat`, 'ok')
      onSaved()
      onClose()
    },
    onError: (error) => toast(error.message, 'error'),
  })
  const set = <K extends keyof UserEdit>(key: K, value: UserEdit[K]) => setEdit({ ...edit, [key]: value })

  const closeOnEscape = useEffectEvent((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  })
  useEffect(() => {
    firstField.current?.focus()
    const onKey = (e: KeyboardEvent) => closeOnEscape(e)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    if (dirty && !passwordProblem) save.mutate(changes)
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby={`${id}-title`}>
        <h2 id={`${id}-title`}>Editează utilizatorul {user.username}</h2>
        <form className={styles.form} onSubmit={submit} noValidate>
          <label className={styles.field}>
            <span>Casă</span>
            <select
              ref={firstField}
              className="input"
              value={edit.houseId}
              disabled={!houses}
              onChange={(e) => set('houseId', e.target.value)}
            >
              <option value="">Fără casă</option>
              {houses?.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </label>
          <div className={styles.field}>
            <span>Rol</span>
            <label className={styles.check}>
              <input
                type="checkbox"
                checked={edit.isAdmin}
                disabled={self}
                aria-describedby={self ? `${id}-self` : undefined}
                onChange={(e) => set('isAdmin', e.target.checked)}
              />
              administrator
            </label>
            {self && (
              <span id={`${id}-self`} className={styles.hint}>
                Nu îți poți retrage propriul rol de administrator.
              </span>
            )}
          </div>
          <div className={styles.field}>
            <label htmlFor={`${id}-password`}>Parolă nouă</label>
            <input
              id={`${id}-password`}
              className="input"
              type="password"
              autoComplete="new-password"
              placeholder="goală = rămâne cea veche"
              value={edit.password}
              onChange={(e) => set('password', e.target.value)}
              aria-invalid={submitted && Boolean(passwordProblem)}
              aria-describedby={submitted && passwordProblem ? `${id}-password-error` : undefined}
            />
            {submitted && passwordProblem && (
              <span id={`${id}-password-error`} className={styles.error}>
                {passwordProblem}
              </span>
            )}
          </div>
          <div className={styles.dialogActions}>
            <button type="button" className="btn" onClick={onClose}>
              Renunță
            </button>
            <button type="submit" className="btn btn-primary" disabled={!dirty || save.isPending}>
              {save.isPending ? 'Se salvează…' : 'Salvează'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function UsersPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const { user: me } = useAuth()
  const [toDelete, setToDelete] = useState<User | null>(null)
  const [editing, setEditing] = useState<User | null>(null)
  const users = useQuery({ queryKey: ['users'], queryFn: api.users })
  const houses = useQuery({ queryKey: ['houses'], queryFn: api.houses })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['users'] })
    void queryClient.invalidateQueries({ queryKey: ['houses'] })
  }
  const remove = useMutation({
    mutationFn: (user: User) => api.deleteUser(user.user_id),
    onSuccess: (_res, user) => {
      toast(`Utilizatorul ${user.username} a fost șters`, 'ok')
      refresh()
    },
    onError: (error) => toast(error.message, 'error'),
  })

  return (
    <div className={styles.page}>
      <Card title="Utilizatori" subtitle="Conturile aplicației și casa fiecăruia. Administratorii pot intra și în acest panou.">
        {users.isPending ? (
          <Spinner label="Se încarcă utilizatorii…" />
        ) : users.isError ? (
          <p className="muted">{users.error.message}</p>
        ) : (
          <div className={tableStyles.wrap}>
            <table className={tableStyles.table}>
              <thead>
                <tr>
                  <th>Utilizator</th>
                  <th>Rol</th>
                  <th>Casă</th>
                  <th>Creat la</th>
                  <th className={tableStyles.right}>Acțiuni</th>
                </tr>
              </thead>
              <tbody>
                {[...users.data].sort((a, b) => a.username.localeCompare(b.username, 'ro', { numeric: true })).map((u) => {
                  const self = u.user_id === me?.user_id
                  return (
                    <tr key={u.user_id}>
                      <td>
                        <strong>{u.username}</strong>
                        {self && <span className="muted"> (tu)</span>}
                      </td>
                      <td>
                        <span className={clsx(tableStyles.pill, u.is_admin ? tableStyles.pillOk : tableStyles.pillOff)}>
                          {u.is_admin ? 'administrator' : 'utilizator'}
                        </span>
                      </td>
                      <td className={clsx(u.house_id === null && 'muted')}>
                        {u.house_id === null ? 'fără casă' : (u.house_name ?? `Casa ${u.house_id}`)}
                      </td>
                      <td className="num">{formatDate(u.created_at)}</td>
                      <td className={tableStyles.right}>
                        <span className={styles.rowActions}>
                          <button
                            type="button"
                            className={clsx('btn', styles.rowButton)}
                            aria-label={`Editează utilizatorul ${u.username}`}
                            onClick={() => setEditing(u)}
                          >
                            Editează
                          </button>
                          <button
                            type="button"
                            className={clsx('btn btn-danger', styles.rowButton)}
                            disabled={self || remove.isPending}
                            title={self ? 'Nu îți poți șterge propriul cont' : undefined}
                            aria-label={`Șterge utilizatorul ${u.username}`}
                            onClick={() => setToDelete(u)}
                          >
                            Șterge
                          </button>
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Utilizator nou" subtitle="Contul poate fi folosit imediat în aplicația de telefon">
        <NewUserForm houses={houses.data && users.data ? freeHouses(houses.data, users.data) : undefined} onCreated={refresh} />
      </Card>

      {editing && (
        <EditUserDialog
          key={editing.user_id}
          user={editing}
          self={editing.user_id === me?.user_id}
          houses={
            houses.data && users.data
              ? freeHouses(houses.data, users.data.filter((u) => u.user_id !== editing.user_id))
              : undefined
          }
          onClose={() => setEditing(null)}
          onSaved={refresh}
        />
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title={`Ștergi utilizatorul ${toDelete?.username ?? ''}?`}
        message="Contul nu se mai poate autentifica. Casa lui, cu bateria, dispozitivele și portofelul, rămâne în simulare fără utilizator."
        confirmLabel="Șterge"
        onCancel={() => setToDelete(null)}
        onConfirm={() => {
          if (toDelete) remove.mutate(toDelete)
          setToDelete(null)
        }}
      />
    </div>
  )
}
