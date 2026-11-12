import { describe, expect, it } from 'vitest'
import type { House, User } from '../types/api'
import { editOf, freeHouses, toNewUser, userChanges, validateUser, type UserDraft } from './users'

const draft = (changes: Partial<UserDraft> = {}): UserDraft => ({
  username: 'casa.noua-1',
  password: 'parola',
  houseId: '',
  isAdmin: false,
  ...changes,
})

describe('validateUser', () => {
  it('accepts a name and a password the server accepts', () => {
    expect(validateUser(draft())).toEqual({})
    expect(validateUser(draft({ username: 'ab_', password: 'abc' }))).toEqual({})
  })

  it('refuses a name that is too short or too long', () => {
    expect(validateUser(draft({ username: 'ab' })).username).toMatch(/între 3 și 50/)
    expect(validateUser(draft({ username: 'a'.repeat(51) })).username).toMatch(/între 3 și 50/)
    expect(validateUser(draft({ username: 'a'.repeat(50) })).username).toBeUndefined()
  })

  it('ignores the spaces around the name but not the ones inside', () => {
    expect(validateUser(draft({ username: '  ana  ' })).username).toBeUndefined()
    expect(validateUser(draft({ username: 'ana maria' })).username).toMatch(/doar litere/)
  })

  it('refuses diacritics and other signs in the name', () => {
    expect(validateUser(draft({ username: 'ștefan' })).username).toMatch(/doar litere/)
    expect(validateUser(draft({ username: 'ana@casa' })).username).toMatch(/doar litere/)
  })

  it('refuses a password under 3 characters', () => {
    expect(validateUser(draft({ password: 'ab' })).password).toMatch(/cel puțin 3/)
    expect(validateUser(draft({ password: '' })).password).toMatch(/cel puțin 3/)
  })

  it('counts the password limit in bytes, as bcrypt does', () => {
    expect(validateUser(draft({ password: 'a'.repeat(72) })).password).toBeUndefined()
    expect(validateUser(draft({ password: 'a'.repeat(73) })).password).toMatch(/72 de octeți/)
    // 37 letters of two bytes each
    expect(validateUser(draft({ password: 'ă'.repeat(37) })).password).toMatch(/72 de octeți/)
    expect(validateUser(draft({ password: 'ă'.repeat(36) })).password).toBeUndefined()
  })
})

describe('toNewUser', () => {
  it('builds the request body', () => {
    expect(toNewUser(draft({ username: ' ana ', houseId: '4', isAdmin: true }))).toEqual({
      username: 'ana',
      password: 'parola',
      house_id: 4,
      is_admin: true,
    })
    expect(toNewUser(draft()).house_id).toBeNull()
  })
})

describe('userChanges', () => {
  const saved = { user_id: 'u-1', username: 'casa1', house_id: 1, house_name: 'Casa 1', is_admin: false } as User

  it('is empty while nothing was edited', () => {
    expect(userChanges(saved, editOf(saved))).toEqual({})
  })

  it('holds only the edited fields', () => {
    expect(userChanges(saved, { ...editOf(saved), houseId: '3' })).toEqual({ house_id: 3 })
    expect(userChanges(saved, { ...editOf(saved), isAdmin: true })).toEqual({ is_admin: true })
    expect(userChanges(saved, { ...editOf(saved), password: 'alta' })).toEqual({ password: 'alta' })
  })

  it('writes "no house" as 0, the value the server takes the house away for', () => {
    expect(userChanges(saved, { ...editOf(saved), houseId: '' })).toEqual({ house_id: 0 })
    expect(userChanges({ ...saved, house_id: null }, { houseId: '', isAdmin: false, password: '' })).toEqual({})
  })
})

describe('freeHouses', () => {
  it('leaves out the houses that already have a user', () => {
    const houses = [{ id: 1 }, { id: 2 }, { id: 3 }] as House[]
    const users = [{ house_id: 2 }, { house_id: null }] as User[]
    expect(freeHouses(houses, users).map((h) => h.id)).toEqual([1, 3])
  })
})
