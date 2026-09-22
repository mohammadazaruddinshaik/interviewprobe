// @vitest-environment jsdom
//
// Task 55 — focused coverage for InterviewResult.jsx: loading, successful
// result rendering (scores, strengths, weaknesses, evidence, per-question
// review), the incomplete-interview state, and API failure/retry/navigation
// behavior. Mocks the API boundary only (../api/interviews.js), same
// approach as the Interview.jsx/InterviewNew.jsx test files.
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/interviews.js', () => ({
  getInterviewResult: vi.fn(),
}))

import { getInterviewResult } from '../api/interviews.js'
import { ApiError } from '../api/client.js'
import InterviewResult from './InterviewResult.jsx'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function makeResult(overrides = {}) {
  const defaults = {
    interview: {
      session_id: 'session-1',
      role: 'AI_ENGINEER',
      difficulty: 'MEDIUM',
      status: 'COMPLETED',
      question_limit: 2,
      started_at: '2026-01-01T00:00:00Z',
      completed_at: '2026-01-01T00:10:00Z',
      created_at: '2026-01-01T00:00:00Z',
    },
    topics: [{ topic: 'RAG', sequence_number: 1, status: 'COMPLETED' }],
    questions: [
      {
        id: 'q1',
        sequence: 1,
        text: 'Explain RAG.',
        topic: 'RAG',
        difficulty: 'MEDIUM',
        type: 'INITIAL',
        candidate_answer: 'RAG grounds generation in retrieved context.',
      },
      {
        id: 'q2',
        sequence: 2,
        text: 'How would you rerank retrieved chunks?',
        topic: 'RAG',
        difficulty: 'MEDIUM',
        type: 'FOLLOW_UP',
        candidate_answer: null,
      },
    ],
    evaluation: {
      session_id: 'session-1',
      technical_knowledge_score: 8.2,
      reasoning_score: 7.1,
      depth_score: 6.4,
      communication_score: 9.0,
      overall_score: 7.7,
      strengths: ['Clearly explained the retrieval step.'],
      weaknesses: ['Limited depth on reranking strategies.'],
      evidence: [
        { question_id: 'q1', topic: 'RAG', claim: 'Understood grounding.', evidence: 'Mentioned retrieved context explicitly.' },
      ],
    },
  }
  return { ...defaults, ...overrides }
}

function renderResult(sessionId = 'session-1') {
  return render(
    <MemoryRouter initialEntries={[`/interview/${sessionId}/result`]}>
      <Routes>
        <Route path="/interview/:sessionId/result" element={<InterviewResult />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('InterviewResult.jsx', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  // -------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------

  it('renders the loading skeleton until getInterviewResult resolves', async () => {
    const { promise, resolve } = deferred()
    getInterviewResult.mockReturnValue(promise)

    renderResult()

    expect(screen.getByText('Loading your results…')).toBeTruthy()

    resolve(makeResult())

    await waitFor(() => expect(screen.getByText('Interview complete')).toBeTruthy())
    expect(screen.queryByText('Loading your results…')).toBeNull()
  })

  // -------------------------------------------------------------------
  // Successful rendering — scores, metadata, strengths, weaknesses,
  // evidence, per-question review
  // -------------------------------------------------------------------

  it('renders the overall score and interview metadata', async () => {
    getInterviewResult.mockResolvedValue(makeResult())

    renderResult()

    await waitFor(() => expect(screen.getByText('7.7')).toBeTruthy())
    // ScoreHero's single metadata line — role/difficulty/question count
    // also appear separately in ResultHeader, so this exact match avoids
    // ambiguity with that duplicate rendering.
    expect(screen.getByText('AI Engineer · Medium · 2 questions')).toBeTruthy()
  })

  it('renders all four score dimensions as accessible progress bars', async () => {
    getInterviewResult.mockResolvedValue(makeResult())

    renderResult()

    await waitFor(() => expect(screen.getByText('7.7')).toBeTruthy())
    expect(screen.getByRole('progressbar', { name: 'Technical Knowledge: 8.2 out of 10' })).toBeTruthy()
    expect(screen.getByRole('progressbar', { name: 'Reasoning: 7.1 out of 10' })).toBeTruthy()
    expect(screen.getByRole('progressbar', { name: 'Depth: 6.4 out of 10' })).toBeTruthy()
    expect(screen.getByRole('progressbar', { name: 'Communication: 9.0 out of 10' })).toBeTruthy()
  })

  it('renders strengths and weaknesses', async () => {
    getInterviewResult.mockResolvedValue(makeResult())

    renderResult()

    await waitFor(() => expect(screen.getByText('Clearly explained the retrieval step.')).toBeTruthy())
    expect(screen.getByText('Limited depth on reranking strategies.')).toBeTruthy()
  })

  it('shows the empty-state message when there are no strengths or weaknesses', async () => {
    getInterviewResult.mockResolvedValue(
      makeResult({
        evaluation: {
          ...makeResult().evaluation,
          strengths: [],
          weaknesses: [],
        },
      }),
    )

    renderResult()

    await waitFor(() =>
      expect(screen.getByText('No specific strengths were identified for this interview.')).toBeTruthy(),
    )
    expect(screen.getByText('No specific areas for improvement were identified.')).toBeTruthy()
  })

  it('renders evidence linked back to its question', async () => {
    getInterviewResult.mockResolvedValue(makeResult())

    renderResult()

    await waitFor(() => expect(screen.getByText('Evidence (1)')).toBeTruthy())
    expect(screen.getByText(/Understood grounding\./)).toBeTruthy()
    expect(screen.getByText(/Mentioned retrieved context explicitly\./)).toBeTruthy()
    // "Question 1 · RAG" is also QuestionReview's own summary label for
    // the same question, so this evidence item's label is one of
    // (at least) two matching nodes rather than the only one.
    expect(screen.getAllByText('Question 1 · RAG').length).toBeGreaterThanOrEqual(1)
  })

  it('does not render an evidence section when there is no evidence', async () => {
    getInterviewResult.mockResolvedValue(
      makeResult({ evaluation: { ...makeResult().evaluation, evidence: [] } }),
    )

    renderResult()

    await waitFor(() => expect(screen.getByText('Interview complete')).toBeTruthy())
    expect(screen.queryByText(/^Evidence/)).toBeNull()
  })

  it('renders per-question review, with the candidate answer and a "no answer" placeholder', async () => {
    getInterviewResult.mockResolvedValue(makeResult())

    renderResult()

    await waitFor(() => expect(screen.getByText('Explain RAG.')).toBeTruthy())
    // Question 1's <details> is open by default (index === 0).
    expect(screen.getByText('RAG grounds generation in retrieved context.')).toBeTruthy()

    // Question 2 has no candidate answer — open it and confirm the
    // placeholder, exercising the review's actual expand interaction.
    fireEvent.click(screen.getByText('How would you rerank retrieved chunks?'))
    expect(screen.getByText('No answer submitted.')).toBeTruthy()
  })

  // -------------------------------------------------------------------
  // Incomplete interview
  // -------------------------------------------------------------------

  it('shows the incomplete-interview message with a link back to the interview when not yet COMPLETED', async () => {
    getInterviewResult.mockRejectedValueOnce(
      new ApiError('Interview is not COMPLETED.', { status: 409, code: 'INVALID_INTERVIEW_STATE' }),
    )

    renderResult('session-2')

    await waitFor(() =>
      expect(screen.getByText('Complete your interview before viewing results.')).toBeTruthy(),
    )
    const continueLink = screen.getByRole('link', { name: 'Continue interview' })
    expect(continueLink.getAttribute('href')).toBe('/interview/session-2')
  })

  // -------------------------------------------------------------------
  // API failure / not-found / retry / navigation
  // -------------------------------------------------------------------

  it('shows a not-found error message and retries on demand', async () => {
    getInterviewResult.mockRejectedValueOnce(new ApiError("We couldn't find what you were looking for.", { status: 404 }))

    renderResult()

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveProperty('textContent', "We couldn't find what you were looking for."),
    )
    expect(screen.getByRole('link', { name: 'Back to home' })).toHaveProperty('href', expect.stringContaining('/'))

    getInterviewResult.mockResolvedValueOnce(makeResult())
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(screen.getByText('Interview complete')).toBeTruthy())
    expect(getInterviewResult).toHaveBeenCalledTimes(2)
  })

  it('falls back to a generic message for a non-ApiError load failure', async () => {
    getInterviewResult.mockRejectedValueOnce(new Error('boom'))

    renderResult()

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveProperty(
        'textContent',
        'Something went wrong while loading your results.',
      ),
    )
  })

  // -------------------------------------------------------------------
  // Navigation out of the result page
  // -------------------------------------------------------------------

  it('offers links to practice again and back to home', async () => {
    getInterviewResult.mockResolvedValue(makeResult())

    renderResult()

    await waitFor(() => expect(screen.getByText('Interview complete')).toBeTruthy())
    expect(screen.getByRole('link', { name: /Practice again/ }).getAttribute('href')).toBe('/interview/new')
    expect(screen.getAllByRole('link', { name: 'Back to home' })[0].getAttribute('href')).toBe('/')
  })
})
