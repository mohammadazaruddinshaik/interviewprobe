// Minimal API client for the InterviewProbe backend.
//
// Authentication is an HttpOnly session cookie set by the backend, so every
// request is sent with `credentials: 'include'`. No token is ever read,
// stored (localStorage/sessionStorage) or put in a URL by the frontend.

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api/v1'

export const NETWORK_ERROR_CODE = 'NETWORK_ERROR'

export class ApiError extends Error {
  readonly status: number
  readonly code: string | null
  /** Seconds from a `Retry-After` header, when the server sent one AND the browser may read it (see note below). */
  readonly retryAfterSeconds: number | null

  constructor(status: number, code: string | null, message: string, retryAfterSeconds: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfterSeconds = retryAfterSeconds
  }

  /** True when no HTTP response was received at all (offline, DNS, CORS, dropped connection). */
  get isNetworkError(): boolean {
    return this.status === 0
  }
}

// Note: for cross-origin requests the browser only exposes `Retry-After` to JavaScript if the server lists it in
// `Access-Control-Expose-Headers`. When it is not exposed this is simply null and callers must use a fallback.
function parseRetryAfter(response: Response): number | null {
  const raw = response.headers.get('Retry-After')
  if (!raw) return null
  const seconds = Number(raw)
  return Number.isFinite(seconds) && seconds >= 0 ? Math.ceil(seconds) : null
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...init.headers },
    })
  } catch {
    // fetch rejects (TypeError) when no response arrives. For a request that may already have been applied
    // (e.g. submitting an answer) the outcome is therefore UNCERTAIN; callers recognise it via isNetworkError.
    throw new ApiError(0, NETWORK_ERROR_CODE, 'The connection to InterviewProbe was interrupted.')
  }

  if (response.status === 204) return undefined as T

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = body?.error
    throw new ApiError(response.status, error?.code ?? null, error?.message ?? response.statusText, parseRetryAfter(response))
  }
  return (body?.data ?? body) as T
}
