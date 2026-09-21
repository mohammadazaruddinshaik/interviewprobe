// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
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

import { getInterview, startInterview } from '../api/interviews.js'
import { useVoiceInterviewSession } from '../voice/useVoiceInterviewSession.js'
import Interview from './Interview.jsx'

const QUESTION_TEXT = 'Explain how a Redis distributed lock works.'
const ANSWER_PLACEHOLDER = 'Explain your approach, reasoning, and trade-offs...'

function mockVoiceSession(voiceMode) {
  useVoiceInterviewSession.mockReturnValue({
    state: { ...createInitialVoiceState(), voiceMode },
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

function renderInterview() {
  return render(
    <MemoryRouter initialEntries={['/interview/session-1']}>
      <Routes>
        <Route path="/interview/:sessionId" element={<Interview />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Interview.jsx text/voice mode switching', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getInterview.mockResolvedValue({ status: 'CREATED', role: 'ai-engineer', difficulty: 'medium', question_limit: 4 })
    startInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q1', sequence: 1, text: QUESTION_TEXT, topic: 'llm' },
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('12. voiceMode=false renders the existing text UI (QuestionPanel + AnswerEditor) unchanged', async () => {
    mockVoiceSession(false)

    renderInterview()

    await waitFor(() => expect(screen.getByText(QUESTION_TEXT)).toBeTruthy())
    expect(screen.getByPlaceholderText(ANSWER_PLACEHOLDER)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Submit answer' })).toBeTruthy()
    // The room's persona identity must NOT be present in text mode.
    expect(screen.queryByText('Azaruddin')).toBeNull()
  })

  it('13. voiceMode=true renders the voice room instead of QuestionPanel/AnswerEditor', async () => {
    mockVoiceSession(true)

    renderInterview()

    await waitFor(() => expect(screen.getByText(QUESTION_TEXT)).toBeTruthy())
    expect(screen.getAllByText('Azaruddin').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('AI Technical Interviewer')).toBeTruthy()
    // The plain text-mode answer textarea (by its distinct placeholder) must
    // not be present — the room renders its own answer surface instead.
    expect(screen.queryByPlaceholderText(ANSWER_PLACEHOLDER)).toBeNull()
  })
})
