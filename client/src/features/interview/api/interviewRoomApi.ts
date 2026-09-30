import { apiRequest } from '@/lib/api'
import type { InterviewState, SubmitAnswerResponse } from '../types/interview'

const base = (id: string) => `/interviews/${encodeURIComponent(id)}`

export const getInterview = (id: string) => apiRequest<InterviewState>(base(id))

export const submitAnswer = (id: string, attempt: { key: string; questionId: string; answer: string }) =>
  apiRequest<SubmitAnswerResponse>(`${base(id)}/answers`, {
    method: 'POST',
    headers: { 'Idempotency-Key': attempt.key },
    body: JSON.stringify({ question_id: attempt.questionId, answer: attempt.answer }),
  })

/** Explicit early exit only — never after an END answer response (the backend has already completed it). */
export const completeInterview = (id: string) =>
  apiRequest<{ session_id: string; status: string }>(`${base(id)}/complete`, { method: 'POST' })
