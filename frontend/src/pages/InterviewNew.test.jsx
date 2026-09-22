// @vitest-environment jsdom
//
// Task 55 — focused coverage for InterviewNew.jsx: role/difficulty/topic
// selection, the question-count stepper, required-configuration
// validation, successful creation + navigation, and API failure/loading
// behavior. Mocks the API boundary (../api/interviews.js) and react-router's
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
import InterviewNew from './InterviewNew.jsx'

const START_LABEL = 'Start interview'

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

describe('InterviewNew.jsx', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  // -------------------------------------------------------------------
  // Defaults + required-configuration validation
  // -------------------------------------------------------------------

  it('defaults to the first role, MEDIUM difficulty, no topics selected, and a disabled submit', () => {
    renderInterviewNew()

    expect(screen.getByRole('button', { name: /AI Engineer/ })).toHaveProperty('ariaPressed', 'true')
    expect(screen.getByRole('button', { name: 'Medium' })).toHaveProperty('ariaPressed', 'true')
    expect(screen.getByText('0 of 6 selected')).toBeTruthy()
    expect(screen.getByRole('button', { name: START_LABEL })).toHaveProperty('disabled', true)
    expect(screen.getByText('You must select at least one topic to start.')).toBeTruthy()
  })

  it('does not call createInterview when the submit button is disabled (no topics selected)', () => {
    renderInterviewNew()

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    expect(createInterview).not.toHaveBeenCalled()
  })

  // -------------------------------------------------------------------
  // Role selection
  // -------------------------------------------------------------------

  it('switches the topic catalog and resets selected topics when the role changes', () => {
    renderInterviewNew()

    fireEvent.click(screen.getByRole('button', { name: 'RAG' }))
    expect(screen.getByText('1 of 6 selected')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Frontend Developer/ }))

    expect(screen.getByRole('button', { name: /Frontend Developer/ })).toHaveProperty('ariaPressed', 'true')
    expect(screen.getByRole('button', { name: /AI Engineer/ })).toHaveProperty('ariaPressed', 'false')
    // AI_ENGINEER's topics are gone, Frontend Developer's are shown instead.
    expect(screen.queryByRole('button', { name: 'RAG' })).toBeNull()
    expect(screen.getByRole('button', { name: 'React' })).toBeTruthy()
    // Selection was cleared by the role change.
    expect(screen.getByText('0 of 6 selected')).toBeTruthy()
    expect(screen.getByRole('button', { name: START_LABEL })).toHaveProperty('disabled', true)
  })

  // -------------------------------------------------------------------
  // Difficulty selection
  // -------------------------------------------------------------------

  it('selects a difficulty and deselects the previous one', () => {
    renderInterviewNew()

    fireEvent.click(screen.getByRole('button', { name: 'Hard' }))

    expect(screen.getByRole('button', { name: 'Hard' })).toHaveProperty('ariaPressed', 'true')
    expect(screen.getByRole('button', { name: 'Medium' })).toHaveProperty('ariaPressed', 'false')
  })

  // -------------------------------------------------------------------
  // Topic selection
  // -------------------------------------------------------------------

  it('toggles a topic on and back off, and enables/disables submit accordingly', () => {
    renderInterviewNew()
    const ragButton = screen.getByRole('button', { name: 'RAG' })

    fireEvent.click(ragButton)
    expect(ragButton).toHaveProperty('ariaPressed', 'true')
    expect(screen.getByRole('button', { name: START_LABEL })).toHaveProperty('disabled', false)

    fireEvent.click(ragButton)
    expect(ragButton).toHaveProperty('ariaPressed', 'false')
    expect(screen.getByRole('button', { name: START_LABEL })).toHaveProperty('disabled', true)
  })

  it('allows selecting multiple topics and reflects the running count', () => {
    renderInterviewNew()

    fireEvent.click(screen.getByRole('button', { name: 'RAG' }))
    fireEvent.click(screen.getByRole('button', { name: 'AI Agents' }))

    expect(screen.getByText('2 of 6 selected')).toBeTruthy()
  })

  // -------------------------------------------------------------------
  // Question-count stepper
  // -------------------------------------------------------------------

  function questionCountValue() {
    // Scoped to the counter's own element: the "Select topics" section
    // heading also renders a bare "3" step-index badge, which would
    // otherwise collide with MIN_QUESTIONS via a plain text query.
    return screen.getByText(/^\d+$/, { selector: 'span[aria-live="polite"]' })
  }

  it('increments and decrements the question count within its bounds', () => {
    renderInterviewNew()
    const increase = screen.getByRole('button', { name: 'Increase number of questions' })
    const decrease = screen.getByRole('button', { name: 'Decrease number of questions' })

    expect(questionCountValue()).toHaveProperty('textContent', '6') // DEFAULT_QUESTION_COUNT

    fireEvent.click(increase)
    expect(questionCountValue()).toHaveProperty('textContent', '7')

    fireEvent.click(decrease)
    fireEvent.click(decrease)
    expect(questionCountValue()).toHaveProperty('textContent', '5')
  })

  it('disables the decrease button at the minimum and the increase button at the maximum', () => {
    renderInterviewNew()
    const increase = screen.getByRole('button', { name: 'Increase number of questions' })
    const decrease = screen.getByRole('button', { name: 'Decrease number of questions' })

    for (let i = 0; i < 10; i += 1) fireEvent.click(decrease)
    expect(questionCountValue()).toHaveProperty('textContent', '3') // MIN_QUESTIONS
    expect(decrease).toHaveProperty('disabled', true)

    for (let i = 0; i < 10; i += 1) fireEvent.click(increase)
    expect(questionCountValue()).toHaveProperty('textContent', '10') // MAX_QUESTIONS
    expect(increase).toHaveProperty('disabled', true)
  })

  // -------------------------------------------------------------------
  // Successful creation + navigation
  // -------------------------------------------------------------------

  it('creates the interview with the selected configuration and navigates to it', async () => {
    renderInterviewNew()
    fireEvent.click(screen.getByRole('button', { name: 'RAG' }))
    fireEvent.click(screen.getByRole('button', { name: 'Hard' }))
    fireEvent.click(screen.getByRole('button', { name: 'Increase number of questions' }))
    createInterview.mockResolvedValue({ id: 'new-session-42' })

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/new-session-42'))
    expect(createInterview).toHaveBeenCalledWith({
      role: 'AI_ENGINEER',
      difficulty: 'HARD',
      topics: ['RAG'],
      questionLimit: 7,
    })
  })

  // -------------------------------------------------------------------
  // Loading / submit behavior
  // -------------------------------------------------------------------

  it('shows the busy submit state while creation is in flight', async () => {
    renderInterviewNew()
    fireEvent.click(screen.getByRole('button', { name: 'RAG' }))
    const { promise, resolve } = deferred()
    createInterview.mockReturnValue(promise)

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    const busyButton = await screen.findByRole('button', { name: 'Starting interview…' })
    expect(busyButton).toHaveProperty('disabled', true)

    resolve({ id: 'session-x' })
    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/session-x'))
  })

  // -------------------------------------------------------------------
  // API failure / error display
  // -------------------------------------------------------------------

  it('shows the API error message on creation failure and re-enables the form', async () => {
    renderInterviewNew()
    fireEvent.click(screen.getByRole('button', { name: 'RAG' }))
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

  it('falls back to a generic message for a non-ApiError creation failure', async () => {
    renderInterviewNew()
    fireEvent.click(screen.getByRole('button', { name: 'RAG' }))
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
