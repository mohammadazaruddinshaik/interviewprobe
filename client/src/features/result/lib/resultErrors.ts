import { ApiError } from '@/lib/api'
import type { InterviewResult } from '../types/result'

export type ResultFailure =
  | { kind: 'unauthenticated' }
  | { kind: 'notFound' }
  | { kind: 'notCompleted' } // 409 INVALID_INTERVIEW_STATE: look up the real status
  | { kind: 'busy' } // 409 EVALUATION_BUSY: another request is generating the evaluation
  | { kind: 'evaluationFailed' } // generation failed; nothing was persisted, so retrying is safe
  | { kind: 'loadError' } // network failure, malformed data, anything else

export function classifyResultError(error: unknown): ResultFailure {
  if (!(error instanceof ApiError) || error.isNetworkError) return { kind: 'loadError' }
  if (error.status === 401) return { kind: 'unauthenticated' }
  if (error.status === 404) return { kind: 'notFound' }
  if (error.status === 409) {
    if (error.code === 'EVALUATION_BUSY') return { kind: 'busy' }
    if (error.code === 'INVALID_INTERVIEW_STATE') return { kind: 'notCompleted' }
    return { kind: 'loadError' }
  }
  if (error.code?.startsWith('AI_SERVICE_') || error.status === 503) return { kind: 'evaluationFailed' }
  return { kind: 'loadError' }
}

const isScore = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const isStringArray = (value: unknown): value is string[] => Array.isArray(value) && value.every((v) => typeof v === 'string')

/** Minimal structural check so a malformed response becomes a retryable error instead of a crash. */
export function isValidResult(value: unknown): value is InterviewResult {
  if (!value || typeof value !== 'object') return false
  const r = value as Partial<InterviewResult>
  const e = r.evaluation
  return (
    !!r.interview &&
    typeof r.interview.role === 'string' &&
    typeof r.interview.difficulty === 'string' &&
    Array.isArray(r.topics) &&
    Array.isArray(r.questions) &&
    !!e &&
    [e.technical_knowledge_score, e.reasoning_score, e.depth_score, e.communication_score, e.overall_score].every(isScore) &&
    isStringArray(e.strengths) &&
    isStringArray(e.weaknesses) &&
    Array.isArray(e.evidence)
  )
}
