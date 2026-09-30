import { ApiError, apiRequest } from './api'

export interface AuthUser {
  id: string
  name: string
  email: string
  avatar_url: string | null
}

interface AuthResponse {
  user: AuthUser
}

/** Exchange a Google Sign-In ID token (the `credential` from Google Identity Services) for a session cookie. */
export async function signInWithGoogle(credential: string): Promise<AuthUser> {
  const { user } = await apiRequest<AuthResponse>('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  })
  return user
}

/** The currently signed-in user, or null when there is no valid session. */
export async function getCurrentUser(): Promise<AuthUser | null> {
  try {
    const { user } = await apiRequest<AuthResponse>('/auth/me')
    return user
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

export async function logout(): Promise<void> {
  await apiRequest<void>('/auth/logout', { method: 'POST' })
}
