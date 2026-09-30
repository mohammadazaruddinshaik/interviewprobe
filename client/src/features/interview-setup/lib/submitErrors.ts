import { ApiError } from '@/lib/api'

export type SubmitFailure = { kind: 'unauthenticated' } | { kind: 'message'; message: string }

/** Maps a failed create/start call to a friendly message; raw backend text is never shown. */
export function describeSubmitFailure(error: unknown): SubmitFailure {
  if (error instanceof ApiError) {
    if (error.status === 401) return { kind: 'unauthenticated' }
    if (error.status === 429) {
      return { kind: 'message', message: 'You’re moving a little fast. Please wait a moment, then try again.' }
    }
    if (error.status === 422) {
      return {
        kind: 'message',
        message: 'Those selections can’t be combined. Adjust your role or focus areas and try again.',
      }
    }
  }
  return { kind: 'message', message: 'Something went wrong on our side. Please try again.' }
}
