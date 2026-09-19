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
// { session_id, status, question: { id, sequence, text, topic, difficulty, type } }
// Only valid while the session is CREATED — the backend returns 409
// (INVALID_INTERVIEW_STATE) otherwise.
export async function startInterview(sessionId) {
  const response = await apiClient.post(`/interviews/${sessionId}/start`)
  return response.data
}

// POST /interviews/{id}/answers -> DataResponse[SubmitAnswerResponse]:
// { session_id, status, action, question: {...} | null, evaluation_status }
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
