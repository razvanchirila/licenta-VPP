import type { House, NewUser, User, UserUpdate } from '../types/api'

// the same rules as Username and Password in the server's request schemas
const USERNAME_MIN = 3
const USERNAME_MAX = 50
const USERNAME_PATTERN = /^[A-Za-z0-9_.-]+$/
const PASSWORD_MIN = 3
export const PASSWORD_MAX_BYTES = 72

export interface UserDraft {
  username: string
  password: string
  /** '' = no house */
  houseId: string
  isAdmin: boolean
}

export const emptyUserDraft: UserDraft = { username: '', password: '', houseId: '', isAdmin: false }

export interface UserDraftErrors {
  username?: string
  password?: string
}

// the server counts characters for the minimum and UTF-8 bytes for the maximum (the bcrypt limit)
export function passwordError(password: string): string | undefined {
  if ([...password].length < PASSWORD_MIN) return `Parola are cel puțin ${PASSWORD_MIN} caractere.`
  if (new TextEncoder().encode(password).length > PASSWORD_MAX_BYTES) {
    return `Parola nu poate depăși ${PASSWORD_MAX_BYTES} de octeți (o literă cu diacritice ocupă doi).`
  }
  return undefined
}

export function validateUser(draft: UserDraft): UserDraftErrors {
  const errors: UserDraftErrors = {}
  const username = draft.username.trim()
  if (username.length < USERNAME_MIN || username.length > USERNAME_MAX) {
    errors.username = `Numele are între ${USERNAME_MIN} și ${USERNAME_MAX} de caractere.`
  } else if (!USERNAME_PATTERN.test(username)) {
    errors.username = 'Numele poate conține doar litere fără diacritice, cifre, punct, cratimă și liniuță de subliniere.'
  }

  const password = passwordError(draft.password)
  if (password) errors.password = password
  return errors
}

export function toNewUser(draft: UserDraft): NewUser {
  return {
    username: draft.username.trim(),
    password: draft.password,
    house_id: draft.houseId === '' ? null : Number(draft.houseId),
    is_admin: draft.isAdmin,
  }
}

export interface UserEdit {
  /** '' = no house */
  houseId: string
  isAdmin: boolean
  /** '' = the password stays as it is */
  password: string
}

export function editOf(user: User): UserEdit {
  return { houseId: user.house_id === null ? '' : String(user.house_id), isAdmin: user.is_admin, password: '' }
}

/** Only what differs from the saved user; the server reads house_id 0 as "take the house away". */
export function userChanges(user: User, edit: UserEdit): UserUpdate {
  const changes: UserUpdate = {}
  const houseId = edit.houseId === '' ? null : Number(edit.houseId)
  if (houseId !== user.house_id) changes.house_id = houseId ?? 0
  if (edit.isAdmin !== user.is_admin) changes.is_admin = edit.isAdmin
  if (edit.password !== '') changes.password = edit.password
  return changes
}

/** The houses no account is attached to; the server refuses a second user on the same house. */
export function freeHouses(houses: House[], users: User[]): House[] {
  const taken = new Set(users.map((u) => u.house_id))
  return houses.filter((h) => !taken.has(h.id))
}
