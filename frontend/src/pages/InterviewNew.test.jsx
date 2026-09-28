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
  uploadResume: vi.fn(),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, useNavigate: () => mockNavigate }
})

import { createInterview, uploadResume } from '../api/interviews.js'
import { ApiError } from '../api/client.js'
import { DEFAULT_DIFFICULTY, DEFAULT_QUESTION_COUNT, ROLES } from '../data/interviewCatalog.js'
import InterviewNew from './InterviewNew.jsx'

const START_LABEL = 'Start Interview'

function makeResumeFile(name = 'resume.pdf') {
  return new File(['%PDF-1.4 fake resume content'], name, { type: 'application/pdf' })
}

function selectResumeFile(file = makeResumeFile()) {
  const input = document.querySelector('input[type="file"]')
  fireEvent.change(input, { target: { files: [file] } })
}

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

    expect(screen.getByText('Select Role')).toBeTruthy()
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

    // The redesign's feature list truthfully describes voice as a product
    // capability ("Voice-First Experience") — that's descriptive copy, not
    // a control. What this test actually guards against (per its name) is
    // an interactive mode toggle the candidate could operate; there is none.
    expect(screen.queryByRole('button', { name: /voice/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /text mode/i })).toBeNull()
    expect(screen.queryByRole('radio', { name: /voice|text mode/i })).toBeNull()
    expect(screen.queryByRole('checkbox', { name: /voice|text mode/i })).toBeNull()
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

    const busyButton = await screen.findByRole('button', { name: 'Starting your interview…' })
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

  // -------------------------------------------------------------------
  // Optional resume upload (Phase 2)
  // -------------------------------------------------------------------

  it('renders the resume section as optional, with no upload/session-creation request made yet', () => {
    renderInterviewNew()

    expect(screen.getByText('Resume · Optional')).toBeTruthy()
    expect(screen.getByText('Drop your resume here, or browse')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeTruthy()
    expect(createInterview).not.toHaveBeenCalled()
    expect(uploadResume).not.toHaveBeenCalled()
  })

  it('uploading a resume reserves a session, shows a busy state, then "Resume ready"', async () => {
    renderInterviewNew()
    const { promise, resolve } = deferred()
    createInterview.mockResolvedValue({ id: 'resume-session-1' })
    uploadResume.mockReturnValue(promise)

    selectResumeFile(makeResumeFile('my_resume.pdf'))

    await screen.findByText('Reading your resume')

    resolve({ status: 'READY', session_id: 'resume-session-1', extraction_error: null })

    await screen.findByText('Resume ready')
    expect(screen.getByText('my_resume.pdf')).toBeTruthy()
    expect(createInterview).toHaveBeenCalledTimes(1)
    expect(uploadResume).toHaveBeenCalledWith('resume-session-1', expect.any(File))
  })

  it('starting after a successful resume upload reuses the same session instead of creating a second one', async () => {
    renderInterviewNew()
    createInterview.mockResolvedValue({ id: 'resume-session-reused' })
    uploadResume.mockResolvedValue({ status: 'READY', session_id: 'resume-session-reused', extraction_error: null })

    selectResumeFile()
    await screen.findByText('Resume ready')

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/resume-session-reused'))
    // Exactly one session was ever created — Start Interview did not
    // create a second, resume-less duplicate.
    expect(createInterview).toHaveBeenCalledTimes(1)
  })

  it('a failed extraction shows the failed state with Replace/Skip, never a raw error page', async () => {
    renderInterviewNew()
    createInterview.mockResolvedValue({ id: 'resume-session-failed' })
    uploadResume.mockResolvedValue({
      status: 'FAILED',
      session_id: 'resume-session-failed',
      extraction_error: "Couldn't read this resume.",
    })

    selectResumeFile()

    await screen.findByText("Couldn't read this resume.")
    expect(screen.getByText('Try another PDF or DOCX.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Replace resume' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeTruthy()
  })

  it('a network failure during upload also lands in the failed state, not an unhandled error', async () => {
    renderInterviewNew()
    createInterview.mockResolvedValue({ id: 'resume-session-network-fail' })
    uploadResume.mockRejectedValueOnce(new ApiError("InterviewProbe couldn't reach the interview service. Please try again."))

    selectResumeFile()

    await screen.findByText("InterviewProbe couldn't reach the interview service. Please try again.")
  })

  it('rejects an unsupported file type client-side without ever calling the API', async () => {
    renderInterviewNew()

    selectResumeFile(new File(['not a resume'], 'resume.exe', { type: 'application/octet-stream' }))

    await screen.findByText('Only PDF or DOCX files are supported.')
    expect(createInterview).not.toHaveBeenCalled()
    expect(uploadResume).not.toHaveBeenCalled()
  })

  it('skipping never calls the API and collapses to a reopenable "Add a resume" link', () => {
    renderInterviewNew()

    fireEvent.click(screen.getByRole('button', { name: 'Skip for now' }))

    expect(screen.queryByText('Drop your resume here, or browse')).toBeNull()
    expect(screen.getByRole('button', { name: 'Add a resume' })).toBeTruthy()
    expect(createInterview).not.toHaveBeenCalled()
    expect(uploadResume).not.toHaveBeenCalled()
  })

  it('replacing a ready resume re-opens the picker and uploads the new file', async () => {
    renderInterviewNew()
    createInterview.mockResolvedValue({ id: 'resume-session-replace' })
    uploadResume.mockResolvedValue({ status: 'READY', session_id: 'resume-session-replace', extraction_error: null })

    selectResumeFile(makeResumeFile('first.pdf'))
    await screen.findByText('first.pdf')

    fireEvent.click(screen.getByRole('button', { name: 'Replace' }))
    selectResumeFile(makeResumeFile('second.pdf'))

    await screen.findByText('second.pdf')
    // The same reserved session is reused for the replacement, not a new one.
    expect(createInterview).toHaveBeenCalledTimes(1)
    expect(uploadResume).toHaveBeenCalledTimes(2)
  })

  it('switching roles after reserving a session starts a fresh reservation under the new role', async () => {
    renderInterviewNew()
    createInterview.mockResolvedValueOnce({ id: 'session-role-a' })
    uploadResume.mockResolvedValue({ status: 'READY', session_id: 'session-role-a', extraction_error: null })

    selectResumeFile()
    await screen.findByText('Resume ready')

    fireEvent.click(screen.getByRole('button', { name: /Frontend Developer/ }))
    // The resume section remounts to a clean idle state for the new role.
    expect(screen.getByText('Drop your resume here, or browse')).toBeTruthy()

    createInterview.mockResolvedValueOnce({ id: 'session-role-b' })
    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/session-role-b'))
    expect(createInterview).toHaveBeenCalledTimes(2)
    expect(createInterview).toHaveBeenLastCalledWith(expect.objectContaining({ role: 'FRONTEND_DEVELOPER' }))
  })

  it('never uploads or creates a resume-associated session when the candidate never touches resume upload', async () => {
    renderInterviewNew()
    createInterview.mockResolvedValue({ id: 'plain-session' })

    fireEvent.click(screen.getByRole('button', { name: START_LABEL }))

    await vi.waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/interview/plain-session'))
    expect(uploadResume).not.toHaveBeenCalled()
  })
})
