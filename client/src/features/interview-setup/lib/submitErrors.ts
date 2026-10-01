import { ApiError } from '@/lib/api'

export type SubmitFailure = { kind: 'unauthenticated' } | { kind: 'message'; message: string }

const RESUME_UNREADABLE =
  'We couldn’t read that resume. Try another PDF or DOCX, or remove it to continue without one.'
export const RESUME_FAILED_MESSAGE = RESUME_UNREADABLE

/** Maps a failed resume upload (the interview is created, nothing has started). */
export function describeResumeFailure(error: unknown): SubmitFailure {
  if (error instanceof ApiError) {
    if (error.status === 401) return { kind: 'unauthenticated' }
    if (error.status === 413) return { kind: 'message', message: 'Resumes must be 5 MB or smaller.' }
    if (error.status === 422) return { kind: 'message', message: RESUME_UNREADABLE }
    if (error.status === 429) {
      return { kind: 'message', message: 'You’re moving a little fast. Please wait a moment, then try again.' }
    }
  }
  return { kind: 'message', message: 'We couldn’t upload your resume. Please try again, or remove it to continue without one.' }
}

/** POST /start on an interview that is no longer CREATED (e.g. a retry after a lost response). */
export const isAlreadyStarted = (error: unknown) =>
  error instanceof ApiError && error.status === 409 && error.code === 'INVALID_INTERVIEW_STATE'

/** Maps a failed create/start call to a friendly message; raw backend text is never shown. */
export function describeSubmitFailure(error: unknown): SubmitFailure {
  if (error instanceof ApiError) {
    if (error.status === 401) return { kind: 'unauthenticated' }
    if (error.isNetworkError) {
      return { kind: 'message', message: 'We couldn’t reach InterviewProbe. Check your connection and try again.' }
    }
    if (error.status === 409) {
      return { kind: 'message', message: 'Your interview is still being prepared. Please try again in a moment.' }
    }
    if (error.status === 502 || error.status === 503 || error.status === 504) {
      return { kind: 'message', message: 'We couldn’t prepare your interview just now. Please try again.' }
    }
    if (error.status === 429) {
      return { kind: 'message', message: 'You’re moving a little fast. Please wait a moment, then try again.' }
    }
    if (error.status === 422) {
      return {
        kind: 'message',
        message: 'We couldn’t set up that interview. Please choose a role and try again.',
      }
    }
  }
  return { kind: 'message', message: 'Something went wrong on our side. Please try again.' }
}
