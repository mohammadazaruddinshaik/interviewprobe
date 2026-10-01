import { ApiError } from '@/lib/api'

/** How a failed ANSWER request must be handled. `uncertain` outcomes keep the same attempt (same key). */
export type AnswerFailure =
  | { kind: 'unauthenticated' }
  | { kind: 'notFound' }
  | { kind: 'busy'; message: string }
  | { kind: 'rateLimited'; retryAfterSeconds: number; message: string }
  | { kind: 'unavailable'; message: string }
  | { kind: 'uncertain'; message: string }
  | { kind: 'stale' } // INVALID_QUESTION / INVALID_INTERVIEW_STATE: re-sync from the server
  | { kind: 'keyReused' } // abnormal: re-sync, then discard the attempt
  | { kind: 'invalid'; message: string }

/** Used when the browser cannot read Retry-After (it is not CORS-exposed by the backend). */
export const DEFAULT_RETRY_SECONDS = 10

export function classifyAnswerError(error: unknown): AnswerFailure {
  if (!(error instanceof ApiError)) {
    return { kind: 'uncertain', message: 'Your last answer may not have been received. We’ve kept it — send it again to continue.' }
  }
  if (error.isNetworkError) {
    return { kind: 'uncertain', message: 'Your last answer may not have been received. We’ve kept it — send it again to continue.' }
  }
  switch (error.status) {
    case 401:
      return { kind: 'unauthenticated' }
    case 404:
      return { kind: 'notFound' }
    case 409:
      if (error.code === 'INTERVIEW_BUSY') return { kind: 'busy', message: 'One moment — try again shortly.' }
      if (error.code === 'IDEMPOTENCY_KEY_REUSED') return { kind: 'keyReused' }
      return { kind: 'stale' }
    case 429:
      return {
        kind: 'rateLimited',
        retryAfterSeconds: error.retryAfterSeconds ?? DEFAULT_RETRY_SECONDS,
        message: 'You’re answering a little fast.',
      }
    case 422:
    case 400:
      return { kind: 'invalid', message: 'We couldn’t send that answer. Please try again.' }
    case 503:
      return { kind: 'unavailable', message: 'We couldn’t reach the interview just now. Try again.' }
    default:
      return { kind: 'uncertain', message: 'Your last answer may not have been received. We’ve kept it — send it again to continue.' }
  }
}

export type LoadFailure = 'unauthenticated' | 'notFound' | 'loadError'

export function classifyLoadError(error: unknown): LoadFailure {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'unauthenticated'
    if (error.status === 404) return 'notFound'
  }
  return 'loadError'
}
