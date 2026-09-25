// @vitest-environment jsdom
//
// Focused coverage for InterviewNew.jsx as a Technical Round setup: the
// candidate chooses ONLY a role. Difficulty, topics, question count, and
// voice/text mode are no longer candidate-facing controls — the Technical
// Round derives them internally (see interviewCatalog.js's
// DEFAULT_DIFFICULTY/DEFAULT_QUESTION_COUNT/getDefaultTopicsForRole).
// Mocks the API boundary (../api/interviews.js) and react-router's
// useNavigate, same mocking approach as the existing Interview.jsx tests.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/interviews.js', () => ({
  createInterview: vi.fn(),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, useNavigate: () => mockNavigate }
})

import { createInterview } from '../api/interviews.js'
import { ApiError } from '../api/client.js'
import { DEFAULT_DIFFICULTY, DEFAULT_QUESTION_COUNT, ROLES } from '../data/interviewCatalog.js'
import InterviewNew from './InterviewNew.jsx'

const START_LABEL = 'Start Technical Round'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function renderInterviewNew() {
  return render(
    <MemoryRouter initialEntries={['/interview/new']}>
      <InterviewNew />
    </MemoryRouter>,
  )
}

describe('InterviewNew.jsx — Technical Round setup', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  // -------------------------------------------------------------------
  // Role-only setup surface
  // -------------------------------------------------------------------

  it('1. shows a role selector, defaulting to the first role, with a ready-to-click submit', () => {
    renderInterviewNew()

    expect(screen.getByText('Select your role')).toBeTruthy()
    expect(screen.getByRole('button', { name: /AI Engineer/ })).toHaveProperty('ariaPressed', 'true')
    expect(screen.getByRole('button', { name: START_LABEL })).toHaveProperty('disabled', false)
  })

  it('2. renders no difficulty selection control', () => {
    renderInterviewNew()

    expect(screen.queryByText('Select difficulty')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Easy' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Medium' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Hard' })).toBeNull()
  })

  it('3. renders no topic selection control', () => {
    renderInterviewNew()

    expect(screen.queryByText('Select topics')).toBeNull()
    expect(screen.queryByText(/of \d+ selected/)).toBeNull()
    expect(screen.queryByRole('button', { name: 'RAG' })).toBeNull()
  })

  it('4. renders no question-count selection control', () => {
    renderInterviewNew()

    expect(screen.queryByText('Number of questions')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Increase number of questions' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Decrease number of questions' })).toBeNull()
  })

  it('5. renders no voice/text mode selection control', () => {
    renderInterviewNew()

    expect(screen.queryByText(/voice/i)).toBeNull()
    expect(screen.queryByText(/text mode/i)).toBeNull()
  })

  // -------------------------------------------------------------------
  // Role selection
  // -------------------------------------------------------------------

  it('switches the selected role without exposing any topic/difficulty control', () => {
    renderInterviewNew()

    fireEvent.click(screen.getByRole('button', { name: /Frontend Developer/ }))

    expect(screen.getByRole('button', { name: /Frontend Developer/ })).toHaveProperty('ariaPressed', 'true')
    expect(screen.getByRole('button', { name: /AI Engineer/ })).toHaveProperty('ariaPressed', 'false')
    expect(screen.getByRole('button', { name: START_LABEL })).toHaveProperty('disabled', false)
  })

  // -------------------------------------------------------------------
  // 8. The new roles appear in the role selector; 9. no invalid/duplicate ids
  // -------------------------------------------------------------------

  it('8. lists every Technical Round role, including the newly added ones', () => {
    renderInterviewNew()

    for (const role of ROLES) {
      expect(screen.getByRole('button', { name: new RegExp(role.label) })).toBeTruthy()
    }
    expect(screen.getByRole('button', { name: /Software Development Engineer/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /SDE Intern/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Full Stack Developer/ })).toBeTruthy()
  })

  it('9. the role catalog contains no duplicate or empty role ids', () => {
    const ids = ROLES.map((role) => role.id)
    expect(ids.every((id) => typeof id === 'string' && id.length > 0)).toBe(true)
    expect(new Set(ids).size).toBe(ids.length)
  })

  // -------------------------------------------------------------------
  // 6. Starting the interview sends the selected role correctly
  // -------------------------------------------------------------------

  it('6. creates the interview with the selected role and the Technical Round’s internal defaults', async () => {
    renderInterviewNew()
    fireEvent.click(screen.getByRole('button', { name: /Full Stack Developer/ }))
    createInterview.mockResolvedValue({ id: 'new-session-42' })

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/new-session-42'))
    const fullStackRole = ROLES.find((role) => role.id === 'FULL_STACK_DEVELOPER')
    expect(createInterview).toHaveBeenCalledWith({
      role: 'FULL_STACK_DEVELOPER',
      difficulty: DEFAULT_DIFFICULTY,
      topics: fullStackRole.topics.map((topic) => topic.id),
      questionLimit: DEFAULT_QUESTION_COUNT,
    })
  })

  it('starting without changing the role sends the default (first) role', async () => {
    renderInterviewNew()
    createInterview.mockResolvedValue({ id: 'session-default-role' })

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/session-default-role'))
    expect(createInterview).toHaveBeenCalledWith(expect.objectContaining({ role: ROLES[0].id }))
  })

  // -------------------------------------------------------------------
  // Loading / submit behavior
  // -------------------------------------------------------------------

  it('shows the busy submit state while creation is in flight', async () => {
    renderInterviewNew()
    const { promise, resolve } = deferred()
    createInterview.mockReturnValue(promise)

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    const busyButton = await screen.findByRole('button', { name: 'Starting your Technical Round…' })
    expect(busyButton).toHaveProperty('disabled', true)

    resolve({ id: 'session-x' })
    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/session-x'))
  })

  // -------------------------------------------------------------------
  // 7. Existing error handling still works
  // -------------------------------------------------------------------

  it('7. shows the API error message on creation failure and re-enables the form', async () => {
    renderInterviewNew()
    createInterview.mockRejectedValueOnce(new ApiError('Too many interview creation requests. Please try again later.', { status: 429 }))

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() =>
      expect(screen.getByRole('alert')).toHaveProperty(
        'textContent',
        'Too many interview creation requests. Please try again later.',
      ),
    )
    expect(screen.getByRole('button', { name: START_LABEL })).toHaveProperty('disabled', false)
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('7. falls back to a generic message for a non-ApiError creation failure', async () => {
    renderInterviewNew()
    createInterview.mockRejectedValueOnce(new Error('network down'))

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() =>
      expect(screen.getByRole('alert')).toHaveProperty(
        'textContent',
        'Something went wrong while creating your interview.',
      ),
    )
  })
})
