import type { Turn } from '../hooks/roomReducer'
import type { AnswerAttempt } from '../types/interview'
import { MAX_ANSWER_LENGTH } from './idempotency'

/** Shared by the composer and the mobile bar so both show the same label/disabled logic. */
export function sendButtonState(draft: string, attempt: AnswerAttempt | null, turn: Turn, secondsLeft: number) {
  const trimmed = draft.trim()
  const sameAsAttempt = !!attempt && attempt.answer === trimmed
  const submitting = turn.status === 'submitting'
  const waiting = turn.status === 'rateLimited' && secondsLeft > 0
  const tooLong = draft.trim().length > MAX_ANSWER_LENGTH
  return {
    busy: submitting,
    disabled: trimmed.length === 0 || tooLong || waiting,
    label: waiting ? `Retry in ${secondsLeft}s` : sameAsAttempt && turn.status !== 'answering' ? 'Retry sending' : 'Send answer',
  }
}

