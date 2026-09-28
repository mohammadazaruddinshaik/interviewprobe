import { apiClient } from './client.js'

// Field names and shape match `CreateInterviewRequest` /
// `CreateInterviewResponse` in backend/app/schemas/interview.py exactly —
// verified against the backend source, not guessed.
export async function createInterview({ role, difficulty, topics, questionLimit }) {
  const response = await apiClient.post('/interviews', {
    role,
    difficulty,
    topics,
    question_limit: questionLimit,
  })
  // `POST /interviews` returns { data: { id, role, difficulty, topics, question_limit, status } }
  return response.data
}

// GET /interviews/{id} -> DataResponse[InterviewResponse]:
// { session_id, role, difficulty, status, question_limit, current_topic,
//   current_question_number, questions_answered, topics }
// Note: this does NOT include the current question's id/text — see
// backend/app/schemas/interview.py's InterviewResponse. There is currently
// no endpoint that returns the full pending question for an already
// IN_PROGRESS session; only `start`/`answers` responses carry that.
export async function getInterview(sessionId) {
  const response = await apiClient.get(`/interviews/${sessionId}`)
  return response.data
}

// POST /interviews/{id}/start -> DataResponse[StartInterviewResponse]:
// { session_id, status, question: { id, sequence, text, topic, difficulty, type, lead_in } }
// `lead_in` is a short, optional (string | null) spoken-only conversational
// reaction the LLM generates alongside the question — never persisted, never
// a structural decision, and always null for the very first question of an
// interview (there's no prior answer yet to react to).
// Only valid while the session is CREATED — the backend returns 409
// (INVALID_INTERVIEW_STATE) otherwise.
export async function startInterview(sessionId) {
  const response = await apiClient.post(`/interviews/${sessionId}/start`)
  return response.data
}

// POST /interviews/{id}/answers -> DataResponse[SubmitAnswerResponse]:
// { session_id, status, action, question: { id, sequence, text, topic, difficulty, type, lead_in } | null, evaluation_status }
// `question.lead_in` (string | null) is the same ephemeral, optional,
// spoken-only field as in the /start response above — null when the
// interview just ended (question is null) or when the LLM had nothing to
// react to.
// Requires an `Idempotency-Key` header (1-128 chars) — the backend
// fingerprints {question_id, answer} against it, so retrying with the same
// key AND the same answer replays the original result, while reusing the
// key with a different answer is rejected (409 IDEMPOTENCY_KEY_REUSED).
export async function submitInterviewAnswer(sessionId, { questionId, answer, idempotencyKey }) {
  const response = await apiClient.post(
    `/interviews/${sessionId}/answers`,
    { question_id: questionId, answer },
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  return response.data
}

// POST /interviews/{id}/complete -> DataResponse[CompleteInterviewResponse]:
// { session_id, status, evaluation_status }
// The existing early-completion endpoint (backend/app/api/routes/
// interviews.py). No request body, no idempotency key. Only valid while the
// session is IN_PROGRESS — 409 (INVALID_INTERVIEW_STATE) otherwise, and a
// busy per-interview lock is also rejected. The current unanswered question
// is left unanswered; the result page already handles that case.
export async function completeInterview(sessionId) {
  const response = await apiClient.post(`/interviews/${sessionId}/complete`)
  return response.data
}

// GET /interviews/{id}/result -> DataResponse[InterviewResultResponse]:
// {
//   interview: { session_id, role, difficulty, status, question_limit, started_at, completed_at, created_at },
//   topics: [{ topic, sequence_number, status }],
//   questions: [{ id, sequence, text, topic, difficulty, type, candidate_answer }],
//   evaluation: {
//     session_id, technical_knowledge_score, reasoning_score, depth_score,
//     communication_score, overall_score, strengths, weaknesses,
//     evidence: [{ question_id, topic, claim, evidence }],
//   },
// }
// May lazily generate the evaluation server-side on first call if the
// interview is COMPLETED and none exists yet — the frontend just calls
// this one endpoint and renders whatever comes back, never calling an
// evaluation endpoint separately. 409 (INVALID_INTERVIEW_STATE) means the
// interview isn't COMPLETED yet; 404 means the session doesn't exist.
export async function getInterviewResult(sessionId) {
  const response = await apiClient.get(`/interviews/${sessionId}/result`)
  return response.data
}

// POST /interviews/{id}/resume (multipart/form-data) -> DataResponse[ResumeResponse]:
// { session_id, original_filename, content_type, file_size, status, extraction_error }
// `status` is one of "UPLOADED"|"EXTRACTING"|"PARSING"|"READY"|"FAILED" —
// by the time this resolves, processing has already finished synchronously
// server-side, so in practice only "READY" or "FAILED" is ever observed
// here. A FAILED response is not a thrown error (see ApiError below) —
// it's a normal 200, since the upload request itself succeeded; only the
// file's content couldn't be read. `extraction_error` is a short,
// candidate-safe message only ever set when status is "FAILED". Never
// returns the extracted text or structured profile — this endpoint
// deliberately only ever exposes processing status and safe metadata.
export async function uploadResume(sessionId, file) {
  const formData = new FormData()
  formData.append('resume', file)
  const response = await apiClient.postForm(`/interviews/${sessionId}/resume`, formData)
  return response.data
}
