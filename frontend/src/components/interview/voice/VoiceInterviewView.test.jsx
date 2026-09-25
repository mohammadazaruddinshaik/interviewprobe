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

const QUESTION = {
  id: 'q1',
  sequence: 1,
  text: 'Explain how a Redis distributed lock works.',
  topic: 'redis',
  lead_in: null,
}

function baseProps(overrides = {}) {
  return {
    voice: makeVoice(overrides.voiceOverrides),
    question: QUESTION,
    roleLabel: 'AI Engineer',
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

  it('renders the lead-in as a separate line from the question when present', () => {
    const leadIn = "That's interesting. You mentioned cache invalidation."
    const question = { ...QUESTION, lead_in: leadIn }
    render(<VoiceInterviewView {...baseProps({ question })} />)

    const leadInNode = screen.getByText(leadIn)
    const questionNode = screen.getByText(QUESTION.text)
    expect(leadInNode).toBeTruthy()
    expect(leadInNode).not.toBe(questionNode)
    // Visually secondary: not rendered as the <h2> question heading.
    expect(leadInNode.tagName).not.toBe('H2')
    expect(questionNode.tagName).toBe('H2')
  })

  it('renders no lead-in line when question.lead_in is null', () => {
    render(<VoiceInterviewView {...baseProps({ question: { ...QUESTION, lead_in: null } })} />)
    expect(screen.queryByText(/null/i)).toBeNull()
  })

  it('renders no lead-in line when question.lead_in is absent entirely', () => {
    const { lead_in: _leadIn, ...questionWithoutLeadIn } = QUESTION
    render(<VoiceInterviewView {...baseProps({ question: questionWithoutLeadIn })} />)
    expect(screen.queryByText(/undefined/i)).toBeNull()
    expect(screen.getByText(QUESTION.text)).toBeTruthy()
  })

  it('renders no lead-in line when question.lead_in is whitespace-only', () => {
    render(<VoiceInterviewView {...baseProps({ question: { ...QUESTION, lead_in: '   ' } })} />)
    expect(screen.getByText(QUESTION.text)).toBeTruthy()
  })
})

// A professional Technical Round presentation: the header shows "Technical
// Round" + the selected role, never internal mechanics (question number,
// question limit, topic, difficulty, or action names like FOLLOW_UP/
// DEEP_DIVE/NEW_AREA), and the candidate-facing submit control reads
// "Finish Answer", not "Submit answer".
describe('VoiceInterviewView — Technical Round presentation', () => {
  it('1&2. header shows "Technical Round" and the selected role, dynamically', () => {
    render(<VoiceInterviewView {...baseProps({ roleLabel: 'Backend Developer' })} />)
    expect(screen.getByText('Technical Round')).toBeTruthy()
    expect(screen.getByText('Backend Developer')).toBeTruthy()
  })

  it('2b. a different role label is reflected in the header, not hardcoded', () => {
    render(<VoiceInterviewView {...baseProps({ roleLabel: 'SDE Intern' })} />)
    expect(screen.getByText('SDE Intern')).toBeTruthy()
    expect(screen.queryByText('AI Engineer')).toBeNull()
  })

  it('3&4. does not display question number or question limit', () => {
    render(<VoiceInterviewView {...baseProps({ question: { ...QUESTION, sequence: 3 } })} />)
    expect(screen.queryByText(/Question \d+ of \d+/)).toBeNull()
    expect(screen.queryByText(/^3$/)).toBeNull()
  })

  it('5. does not display the question topic', () => {
    render(<VoiceInterviewView {...baseProps({ question: { ...QUESTION, topic: 'SYSTEM_DESIGN' } })} />)
    expect(screen.queryByText('SYSTEM_DESIGN')).toBeNull()
    expect(screen.queryByText(/system design/i)).toBeNull()
  })

  it('6. does not display the difficulty', () => {
    render(<VoiceInterviewView {...baseProps()} />)
    expect(screen.queryByText('Medium')).toBeNull()
    expect(screen.queryByText('MEDIUM')).toBeNull()
  })

  it('7. does not display internal LangGraph action names', () => {
    render(<VoiceInterviewView {...baseProps()} />)
    for (const action of ['FOLLOW_UP', 'NEW_AREA', 'DEEP_DIVE', 'CLARIFICATION', 'CHALLENGE', 'TOPIC_TRANSITION']) {
      expect(screen.queryByText(action)).toBeNull()
    }
  })

  it('8&9. the question stays the focal point, with the lead-in visible above it when present', () => {
    const leadIn = "That's interesting. You mentioned cache invalidation."
    render(<VoiceInterviewView {...baseProps({ question: { ...QUESTION, lead_in: leadIn } })} />)
    expect(screen.getByText(QUESTION.text)).toBeTruthy()
    expect(screen.getByText(leadIn)).toBeTruthy()
  })

  it('10&11. the candidate control reads "Finish Answer", never "Submit answer"', () => {
    render(<VoiceInterviewView {...baseProps({ answer: 'A complete answer.' })} />)
    expect(screen.getByRole('button', { name: 'Finish Answer' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Submit answer' })).toBeNull()
    expect(screen.queryByText('Submit answer')).toBeNull()
  })

  it('12. clicking Finish Answer still invokes the existing onSubmit callback', () => {
    const props = baseProps({ answer: 'A complete answer.' })
    render(<VoiceInterviewView {...props} />)
    fireEvent.click(screen.getByRole('button', { name: 'Finish Answer' }))
    expect(props.onSubmit).toHaveBeenCalledOnce()
  })

  it('13. listening/speaking/processing states are unaffected by the header/control changes', () => {
    const props = baseProps({
      voiceOverrides: { state: { status: VOICE_STATUS.CANDIDATE_LISTENING }, activeChannel: 'mic', micUiState: 'listening' },
    })
    render(<VoiceInterviewView {...props} />)
    expect(screen.getByText('Listening for your answer')).toBeTruthy()
  })
})
