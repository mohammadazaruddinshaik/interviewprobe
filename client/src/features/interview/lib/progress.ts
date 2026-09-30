import type { Question } from '../types/interview'

/**
 * "Question N of M": N is the current question's sequence, M the backend's question_limit.
 * question_limit counts every generated question (follow-ups included), and the interview may end earlier.
 */
export function questionProgress(question: Question, questionLimit: number) {
  const current = Math.min(Math.max(question.sequence, 1), questionLimit)
  return { current, total: questionLimit, label: `Question ${current} of ${questionLimit}` }
}

const TYPE_LABELS: Record<string, string> = {
  INITIAL: 'Opening question',
  FOLLOW_UP: 'Follow-up',
  CLARIFICATION: 'Clarification',
  DEEP_DIVE: 'Deep dive',
  CHALLENGE: 'Challenge',
  TOPIC_TRANSITION: 'New topic',
}

export const questionTypeLabel = (type: string) =>
  TYPE_LABELS[type] ?? type.charAt(0) + type.slice(1).toLowerCase().replace(/_/g, ' ')
