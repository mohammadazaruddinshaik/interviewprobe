// @vitest-environment jsdom
//
// Task 55 — focused coverage for the TEXT MODE interview lifecycle in
// Interview.jsx: loading, rendering the current question, resumability,
// answering, submitting, the next-question/completion transitions, and
// API error handling. Voice mode is exercised separately (see
// Interview.modeSwitch.test.jsx / Interview.remoteStt.integration.test.jsx
// / Interview.voiceRaceConditions.integration.test.jsx) — every test here
// fixes `voiceMode: false`, same mocking approach as those files.
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createInitialVoiceState } from '../voice/voiceState.js'

vi.mock('../api/interviews.js', () => ({
  getInterview: vi.fn(),
  startInterview: vi.fn(),
  submitInterviewAnswer: vi.fn(),
}))
vi.mock('../voice/useVoiceInterviewSession.js', () => ({
  useVoiceInterviewSession: vi.fn(),
}))

import { getInterview, startInterview, submitInterviewAnswer } from '../api/interviews.js'
import { useVoiceInterviewSession } from '../voice/useVoiceInterviewSession.js'
import { ApiError } from '../api/client.js'
import Interview from './Interview.jsx'

const ANSWER_LABEL = 'Your answer'
const SUBMIT_LABEL = 'Submit answer'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function mockTextMode() {
  useVoiceInterviewSession.mockReturnValue({
    state: { ...createInitialVoiceState(), voiceMode: false },
    activeChannel: null,
    isSpeakerSpeaking: false,
    isSpeakerError: false,
    micUiState: 'idle',
    ttsSupported: true,
    sttSupported: true,
    commands: {
      enableVoiceMode: vi.fn(),
      disableVoiceMode: vi.fn(),
      replayQuestion: vi.fn(),
      stopSpeaking: vi.fn(),
      startListening: vi.fn(),
      stopListening: vi.fn(),
      resetForQuestion: vi.fn(),
      clearError: vi.fn(),
    },
  })
}

function renderInterview(sessionId = 'session-1') {
  return render(
    <MemoryRouter initialEntries={[`/interview/${sessionId}`]}>
      <Routes>
        <Route path="/interview/:sessionId" element={<Interview />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Interview.jsx text-mode lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockTextMode()
  })

  afterEach(() => {
    cleanup()
  })

  // -------------------------------------------------------------------
  // Loading an interview
  // -------------------------------------------------------------------

  it('renders the loading skeleton until getInterview resolves', async () => {
    const { promise, resolve } = deferred()
    getInterview.mockReturnValue(promise)

    renderInterview()

    expect(screen.getByText('Loading your interview…')).toBeTruthy()

    resolve({ status: 'CREATED', role: 'AI_ENGINEER', difficulty: 'MEDIUM', question_limit: 4 })
    startInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q1', sequence: 1, text: 'Explain RAG.', topic: 'RAG' },
    })

    await waitFor(() => expect(screen.getByText('Explain RAG.')).toBeTruthy())
    expect(screen.queryByText('Loading your interview…')).toBeNull()
  })

  // -------------------------------------------------------------------
  // Rendering the current question — a CREATED session starts one
  // -------------------------------------------------------------------

  it('starts a CREATED interview and renders the first question', async () => {
    getInterview.mockResolvedValue({ status: 'CREATED', role: 'AI_ENGINEER', difficulty: 'MEDIUM', question_limit: 4 })
    startInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q1', sequence: 1, text: 'Explain RAG.', topic: 'RAG' },
    })

    renderInterview('session-1')

    await waitFor(() => expect(screen.getByText('Explain RAG.')).toBeTruthy())
    expect(startInterview).toHaveBeenCalledWith('session-1')
    expect(screen.getByText('Question 1 of 4')).toBeTruthy()
    expect(screen.getByLabelText(ANSWER_LABEL)).toBeTruthy()
  })

  // -------------------------------------------------------------------
  // Resumability — an IN_PROGRESS session restores its current question
  // without calling start (start only accepts CREATED sessions)
  // -------------------------------------------------------------------

  it('resumes an IN_PROGRESS interview from its current_question without calling start', async () => {
    getInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      role: 'BACKEND_DEVELOPER',
      difficulty: 'HARD',
      question_limit: 5,
      current_question: { id: 'q3', sequence: 3, text: 'Design a rate limiter.', topic: 'SYSTEM_DESIGN' },
    })

    renderInterview()

    await waitFor(() => expect(screen.getByText('Design a rate limiter.')).toBeTruthy())
    expect(screen.getByText('Question 3 of 5')).toBeTruthy()
    expect(startInterview).not.toHaveBeenCalled()
  })

  it('shows a restore-failed error when an IN_PROGRESS session has no current_question', async () => {
    getInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      role: 'BACKEND_DEVELOPER',
      difficulty: 'HARD',
      question_limit: 5,
      current_question: null,
    })

    renderInterview()

    await waitFor(() =>
      expect(screen.getByText("Interview state couldn't be restored. Please try again.")).toBeTruthy(),
    )
    expect(screen.getByRole('link', { name: 'Start a new interview' })).toBeTruthy()
    expect(startInterview).not.toHaveBeenCalled()
  })

  // -------------------------------------------------------------------
  // Completion state
  // -------------------------------------------------------------------

  it('renders the completed view directly for an already-COMPLETED session', async () => {
    getInterview.mockResolvedValue({ status: 'COMPLETED', role: 'AI_ENGINEER', difficulty: 'MEDIUM', question_limit: 3 })

    renderInterview('session-9')

    await waitFor(() => expect(screen.getByText('Interview complete.')).toBeTruthy())
    expect(screen.getByRole('link', { name: /View results/ })).toHaveProperty(
      'href',
      expect.stringContaining('/interview/session-9/result'),
    )
    expect(startInterview).not.toHaveBeenCalled()
  })

  // -------------------------------------------------------------------
  // Loading errors + retry
  // -------------------------------------------------------------------

  it('shows the API error message on load failure and retries on demand', async () => {
    getInterview.mockRejectedValueOnce(new ApiError('Interview not found.', { status: 404 }))

    renderInterview()

    await waitFor(() => expect(screen.getByRole('alert')).toHaveProperty('textContent', 'Interview not found.'))

    getInterview.mockResolvedValueOnce({ status: 'CREATED', role: 'AI_ENGINEER', difficulty: 'MEDIUM', question_limit: 3 })
    startInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q1', sequence: 1, text: 'Explain RAG.', topic: 'RAG' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(screen.getByText('Explain RAG.')).toBeTruthy())
    expect(getInterview).toHaveBeenCalledTimes(2)
  })

  it('falls back to a generic message for a non-ApiError load failure', async () => {
    getInterview.mockRejectedValueOnce(new Error('boom'))

    renderInterview()

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveProperty(
        'textContent',
        'Something went wrong while loading your interview.',
      ),
    )
  })

  // -------------------------------------------------------------------
  // Entering + submitting an answer, submit/loading/disabled behavior
  // -------------------------------------------------------------------

  async function renderReadyInterview() {
    getInterview.mockResolvedValue({ status: 'CREATED', role: 'AI_ENGINEER', difficulty: 'MEDIUM', question_limit: 2 })
    startInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q1', sequence: 1, text: 'Explain RAG.', topic: 'RAG' },
    })
    renderInterview()
    await waitFor(() => expect(screen.getByText('Explain RAG.')).toBeTruthy())
  }

  it('disables submit until an answer is entered, and enables it once text is typed', async () => {
    await renderReadyInterview()

    const submitButton = screen.getByRole('button', { name: SUBMIT_LABEL })
    expect(submitButton).toHaveProperty('disabled', true)

    fireEvent.change(screen.getByLabelText(ANSWER_LABEL), { target: { value: 'RAG grounds generation in retrieval.' } })

    expect(submitButton).toHaveProperty('disabled', false)
  })

  it('a whitespace-only answer does not enable submit', async () => {
    await renderReadyInterview()

    fireEvent.change(screen.getByLabelText(ANSWER_LABEL), { target: { value: '   ' } })

    expect(screen.getByRole('button', { name: SUBMIT_LABEL })).toHaveProperty('disabled', true)
  })

  it('shows the loading/busy submit state while the request is in flight, then the next question', async () => {
    await renderReadyInterview()
    fireEvent.change(screen.getByLabelText(ANSWER_LABEL), { target: { value: 'RAG grounds generation in retrieval.' } })

    const { promise, resolve } = deferred()
    submitInterviewAnswer.mockReturnValue(promise)

    fireEvent.click(screen.getByRole('button', { name: SUBMIT_LABEL }))

    await waitFor(() => expect(screen.getByRole('button', { name: 'Evaluating your answer…' })).toBeTruthy())
    expect(screen.getByRole('button', { name: 'Evaluating your answer…' })).toHaveProperty('disabled', true)

    resolve({
      status: 'IN_PROGRESS',
      action: 'FOLLOW_UP',
      question: { id: 'q2', sequence: 2, text: 'How would you rerank results?', topic: 'RAG' },
    })

    await waitFor(() => expect(screen.getByText('How would you rerank results?')).toBeTruthy())
    // The answer box is cleared for the next question, and submit is
    // disabled again until new text is entered.
    expect(screen.getByLabelText(ANSWER_LABEL)).toHaveProperty('value', '')
    expect(screen.getByRole('button', { name: SUBMIT_LABEL })).toHaveProperty('disabled', true)
  })

  it('submits with the question id, trimmed answer, and an idempotency key', async () => {
    await renderReadyInterview()
    fireEvent.change(screen.getByLabelText(ANSWER_LABEL), { target: { value: '  RAG grounds generation.  ' } })
    submitInterviewAnswer.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q2', sequence: 2, text: 'Next question.', topic: 'RAG' },
    })

    fireEvent.click(screen.getByRole('button', { name: SUBMIT_LABEL }))

    await waitFor(() => expect(submitInterviewAnswer).toHaveBeenCalledTimes(1))
    const [sessionIdArg, payload] = submitInterviewAnswer.mock.calls[0]
    expect(sessionIdArg).toBe('session-1')
    expect(payload.questionId).toBe('q1')
    expect(payload.answer).toBe('RAG grounds generation.')
    expect(typeof payload.idempotencyKey).toBe('string')
    expect(payload.idempotencyKey.length).toBeGreaterThan(0)
  })

  it('transitions to the completed view when submitting the final answer returns no next question', async () => {
    await renderReadyInterview()
    fireEvent.change(screen.getByLabelText(ANSWER_LABEL), { target: { value: 'Final answer.' } })
    submitInterviewAnswer.mockResolvedValue({ status: 'COMPLETED', action: 'END', question: null })

    fireEvent.click(screen.getByRole('button', { name: SUBMIT_LABEL }))

    await waitFor(() => expect(screen.getByText('Interview complete.')).toBeTruthy())
  })

  it('shows a submit error, keeps the typed answer, and re-enables the submit button', async () => {
    await renderReadyInterview()
    fireEvent.change(screen.getByLabelText(ANSWER_LABEL), { target: { value: 'My answer.' } })
    submitInterviewAnswer.mockRejectedValueOnce(new ApiError('Too many answer submissions. Please try again shortly.', { status: 429 }))

    fireEvent.click(screen.getByRole('button', { name: SUBMIT_LABEL }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveProperty(
        'textContent',
        'Too many answer submissions. Please try again shortly.',
      ),
    )
    // The candidate's work is not lost, and they can retry.
    expect(screen.getByLabelText(ANSWER_LABEL)).toHaveProperty('value', 'My answer.')
    expect(screen.getByRole('button', { name: SUBMIT_LABEL })).toHaveProperty('disabled', false)
  })

  it('falls back to a generic message for a non-ApiError submit failure', async () => {
    await renderReadyInterview()
    fireEvent.change(screen.getByLabelText(ANSWER_LABEL), { target: { value: 'My answer.' } })
    submitInterviewAnswer.mockRejectedValueOnce(new Error('network down'))

    fireEvent.click(screen.getByRole('button', { name: SUBMIT_LABEL }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveProperty(
        'textContent',
        'Something went wrong while submitting your answer.',
      ),
    )
  })
})
