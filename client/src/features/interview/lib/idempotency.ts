import type { AnswerAttempt } from '../types/interview'

export const MAX_ANSWER_LENGTH = 10_000

export type AnswerValidation = { ok: true; answer: string } | { ok: false; message: string }

/** Local validation mirroring the backend (trimmed, non-empty, <= 10,000 characters). */
export function validateAnswer(draft: string): AnswerValidation {
  const answer = draft.trim()
  if (!answer) return { ok: false, message: 'We didn’t catch an answer. Please speak, then finish your answer.' }
  if (answer.length > MAX_ANSWER_LENGTH) {
    return { ok: false, message: `Answers can be up to ${MAX_ANSWER_LENGTH.toLocaleString()} characters.` }
  }
  return { ok: true, answer }
}

const newKey = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `k-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`

/**
 * One key per LOGICAL answer: reuse the existing attempt only when question AND (trimmed) answer are identical.
 * A failed request never changes the key; editing the answer text is a new logical answer and gets a new key.
 */
export function attemptFor(existing: AnswerAttempt | null, questionId: string, answer: string): AnswerAttempt {
  if (existing && existing.questionId === questionId && existing.answer === answer) return existing
  return { key: newKey(), questionId, answer }
}

// sessionStorage holds ONLY {key, questionId, answer} (never auth data). It exists so that a refresh after an
// uncertain submission can reuse the same Idempotency-Key. Every access is guarded: storage can be unavailable.
const storageKey = (interviewId: string) => `interviewprobe:attempt:${interviewId}`

export function loadAttempt(interviewId: string): AnswerAttempt | null {
  try {
    const raw = sessionStorage.getItem(storageKey(interviewId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<AnswerAttempt>
    if (typeof parsed.key === 'string' && typeof parsed.questionId === 'string' && typeof parsed.answer === 'string') {
      return { key: parsed.key, questionId: parsed.questionId, answer: parsed.answer }
    }
  } catch {
    /* unavailable or corrupt: treat as no attempt */
  }
  return null
}

export function saveAttempt(interviewId: string, attempt: AnswerAttempt): void {
  try {
    sessionStorage.setItem(storageKey(interviewId), JSON.stringify(attempt))
  } catch {
    /* the in-memory attempt still protects this page view */
  }
}

export function clearAttempt(interviewId: string): void {
  try {
    sessionStorage.removeItem(storageKey(interviewId))
  } catch {
    /* ignore */
  }
}
