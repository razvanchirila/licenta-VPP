const TOKEN_KEY = 'vpp_admin_token'

// sessionStorage can throw (private mode, blocked storage), so the token is kept in memory and
// storage only carries it over a reload
let current: string | null = readStored()

function readStored(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function loadToken(): string | null {
  return current
}

export function saveToken(token: string): void {
  current = token
  try {
    sessionStorage.setItem(TOKEN_KEY, token)
  } catch {
    /* empty */
  }
}

export function clearToken(): void {
  current = null
  try {
    sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    /* empty */
  }
}
