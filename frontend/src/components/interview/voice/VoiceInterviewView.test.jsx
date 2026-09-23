// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createInitialVoiceState, VOICE_STATUS } from '../../../voice/voiceState.js'
import VoiceInterviewView from './VoiceInterviewView.jsx'

afterEach(() => {
  cleanup()
})

// Builds a deterministic, mocked useVoiceInterviewSession()-shaped object —
// exactly what VoiceInterviewView actually receives, so these tests never
// touch the real hook or any real speech provider.
function makeVoice(overrides = {}) {
  const state = { ...createInitialVoiceState(), ...overrides.state }
  return {
    state,
    activeChannel: overrides.activeChannel ?? null,
    isSpeakerSpeaking: overrides.isSpeakerSpeaking ?? state.status === VOICE_STATUS.INTERVIEWER_SPEAKING,
    isSpeakerError: overrides.isSpeakerError ?? false,
    micUiState: overrides.micUiState ?? 'idle',
    ttsSupported: overrides.ttsSupported ?? true,
    sttSupported: overrides.sttSupported ?? true,
    commands: {
      replayQuestion: vi.fn(),
      stopSpeaking: vi.fn(),
      startListening: vi.fn(),
      stopListening: vi.fn(),
      resetForQuestion: vi.fn(),
      clearError: vi.fn(),
      ...overrides.commands,
    },
  }
}

const QUESTION = { id: 'q1', sequence: 1, text: 'Explain how a Redis distributed lock works.', topic: 'redis' }

function baseProps(overrides = {}) {
  return {
    voice: makeVoice(overrides.voiceOverrides),
    question: QUESTION,
    questionLimit: 4,
    roleLabel: 'AI Engineer',
    difficultyLabel: 'Medium',
    topicLabel: 'Redis',
    answer: '',
    onAnswerChange: vi.fn(),
    onSubmit: vi.fn(),
    submitting: false,
    ...overrides,
  }
}

describe('VoiceInterviewView', () => {
  it('1. renders the interviewer identity', () => {
    render(<VoiceInterviewView {...baseProps()} />)
    // "Azaruddin" legitimately appears twice by design: once in
    // InterviewerIdentity, once as the current-speaker label above the
    // question in InterviewSubtitles.
    expect(screen.getAllByText('Azaruddin').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('AI Technical Interviewer')).toBeTruthy()
  })

  it('2. shows the current question text in the subtitles, verbatim', () => {
    render(<VoiceInterviewView {...baseProps()} />)
    expect(screen.getByText(QUESTION.text)).toBeTruthy()
  })

  it('3. displays the candidate interim transcript when provided', () => {
    const props = baseProps({ voiceOverrides: { state: { status: VOICE_STATUS.CANDIDATE_SPEAKING, interimTranscript: 'I would first check the' } } })
    render(<VoiceInterviewView {...props} />)
    expect(screen.getByText(/I would first check the/)).toBeTruthy()
  })

  it('4. displays the candidate finalized answer', () => {
    render(<VoiceInterviewView {...baseProps({ answer: 'Redis SETNX with a TTL implements the lock.' })} />)
    expect(screen.getByLabelText('Your answer').value).toBe('Redis SETNX with a TTL implements the lock.')
  })

  it('5. shows the interviewer speaking indicator while speaking', () => {
    const props = baseProps({ voiceOverrides: { state: { status: VOICE_STATUS.INTERVIEWER_SPEAKING } } })
    render(<VoiceInterviewView {...props} />)
    expect(screen.getByText('Interviewer speaking')).toBeTruthy()
  })

  it('6. shows the listening indicator while the mic is listening', () => {
    const props = baseProps({
      voiceOverrides: { state: { status: VOICE_STATUS.CANDIDATE_LISTENING }, activeChannel: 'mic', micUiState: 'listening' },
    })
    render(<VoiceInterviewView {...props} />)
    expect(screen.getByText('Listening for your answer')).toBeTruthy()
  })

  it('7. disables the microphone control while processing', () => {
    const props = baseProps({
      voiceOverrides: { state: { status: VOICE_STATUS.PROCESSING }, activeChannel: 'mic', micUiState: 'processing' },
    })
    render(<VoiceInterviewView {...props} />)
    expect(screen.getByRole('button', { name: /Processing/ }).disabled).toBe(true)
  })

  it('8. renders a recoverable, dismissible error', () => {
    const props = baseProps({
      voiceOverrides: {
        state: { status: VOICE_STATUS.ERROR, error: { code: 'no-speech', message: "We didn't catch that.", recoverable: true, source: 'stt' } },
      },
    })
    render(<VoiceInterviewView {...props} />)
    const alert = screen.getByRole('alert')
    expect(alert.textContent).toContain("We didn't catch that.")
    const dismiss = screen.getByRole('button', { name: 'Dismiss' })
    fireEvent.click(dismiss)
    expect(props.voice.commands.clearError).toHaveBeenCalledOnce()
  })

  it('9. replay invokes the session replay command', () => {
    const props = baseProps()
    render(<VoiceInterviewView {...props} />)
    fireEvent.click(screen.getByRole('button', { name: 'Replay question' }))
    expect(props.voice.commands.replayQuestion).toHaveBeenCalledOnce()
  })

  it('10. stop invokes the session stopSpeaking command while speaking', () => {
    const props = baseProps({ voiceOverrides: { state: { status: VOICE_STATUS.INTERVIEWER_SPEAKING } } })
    render(<VoiceInterviewView {...props} />)
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    expect(props.voice.commands.stopSpeaking).toHaveBeenCalledOnce()
  })

  it('11. the microphone control invokes start then stop listening', () => {
    const props = baseProps()
    render(<VoiceInterviewView {...props} />)
    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    expect(props.voice.commands.startListening).toHaveBeenCalledOnce()

    cleanup()
    const listeningProps = baseProps({
      voiceOverrides: { state: { status: VOICE_STATUS.CANDIDATE_LISTENING }, activeChannel: 'mic', micUiState: 'listening' },
    })
    render(<VoiceInterviewView {...listeningProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    expect(listeningProps.voice.commands.stopListening).toHaveBeenCalledOnce()
  })

  it('14. controls are real, focusable buttons', () => {
    render(<VoiceInterviewView {...baseProps()} />)
    const replayButton = screen.getByRole('button', { name: 'Replay question' })
    replayButton.focus()
    expect(document.activeElement).toBe(replayButton)
    expect(replayButton.tagName).toBe('BUTTON')
  })

  it('15. status text is present regardless of a reduced-motion preference (never animation-only)', () => {
    const originalMatchMedia = window.matchMedia
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))

    try {
      const props = baseProps({ voiceOverrides: { state: { status: VOICE_STATUS.INTERVIEWER_SPEAKING } } })
      render(<VoiceInterviewView {...props} />)
      // The status is conveyed as text/aria content, not just a CSS animation
      // class — asserting the text is present is what proves that.
      expect(screen.getByText('Interviewer speaking')).toBeTruthy()
    } finally {
      window.matchMedia = originalMatchMedia
    }
  })

  it('never invents a paraphrased question — renders the exact question text', () => {
    const longQuestion = { ...QUESTION, text: 'A very specific, exact question string that must not be rewritten.' }
    render(<VoiceInterviewView {...baseProps({ question: longQuestion })} />)
    expect(screen.getByText(longQuestion.text)).toBeTruthy()
  })
})
