// Mirrors the backend contract (GET /interviews/{id}, POST /answers, GET /result). Enum-like values stay strings.

export type InterviewStatus = 'CREATED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'

export interface Question {
  id: string
  sequence: number
  text: string
  topic: string
  difficulty: string
  type: string
  /** Only present on the answer response that produced the question; GET never returns it. */
  lead_in: string | null
}

export interface TopicEntry {
  topic: string
  sequence_number: number
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | string
}

/** GET /interviews/{id} */
export interface InterviewState {
  session_id: string
  role: string
  /** Planner-owned: null while CREATED, the real value once started. */
  difficulty: string | null
  status: InterviewStatus
  question_limit: number | null
  current_topic: string | null
  current_question_number: number
  questions_answered: number
  topics: TopicEntry[]
  current_question: Question | null
}

/** POST /interviews/{id}/answers */
export interface SubmitAnswerResponse {
  session_id: string
  status: InterviewStatus
  action: string
  question: Question | null
  evaluation_status: string | null
}

/** One answered turn, kept only in memory for the current browser session. */
export interface TranscriptEntry {
  questionId: string
  sequence: number
  question: string
  answer: string
}

/** The in-flight logical answer; persisted to sessionStorage so a refresh can reuse the same key. */
export interface AnswerAttempt {
  key: string
  questionId: string
  answer: string
}
