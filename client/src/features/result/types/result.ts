// Mirrors GET /api/v1/interviews/{id}/result. Enum-like values stay strings.

export interface ResultInterview {
  session_id: string
  role: string
  difficulty: string
  status: string
  question_limit: number
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface ResultTopic {
  topic: string
  sequence_number: number
  status: string
}

export interface ResultQuestion {
  id: string
  sequence: number
  text: string
  topic: string
  difficulty: string
  type: string
  /** null when the question was never answered. Shown exactly as received. */
  candidate_answer: string | null
}

export interface EvidenceItem {
  claim: string
  evidence: string
  question_id?: string
  topic?: string
}

export interface ResultEvaluation {
  session_id: string
  technical_knowledge_score: number
  reasoning_score: number
  depth_score: number
  communication_score: number
  overall_score: number
  strengths: string[]
  weaknesses: string[]
  evidence: EvidenceItem[]
}

export interface InterviewResult {
  interview: ResultInterview
  topics: ResultTopic[]
  questions: ResultQuestion[]
  evaluation: ResultEvaluation
}
