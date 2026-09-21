// @vitest-environment jsdom
//
// Task 41 §22 — the complete application path with a mocked remote STT
// provider, exercising the REAL useVoiceInterviewSession hook and
// voiceReducer (unlike Interview.modeSwitch.test.jsx, which mocks the hook
// itself). Only the provider factory is faked, matching how remote mode is
// actually selected in production (VITE_STT_MODE=remote just swaps which
// object createVoiceProviders() returns) — VoiceInterviewView,
// useVoiceInterviewSession, and Interview.jsx never know a fake/Deepgram
// implementation is behind it.
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { fakeTts, fakeStt } = vi.hoisted(() => {
  function makeFakeTts() {
    return {
      isSupported: true,
      // Immediately reports "stopped" (never onNaturalEnd/onError) so the
      // auto-speak-on-voice-mode-enable effect gets out of the way without
      // ever locking the mic to the speaker or auto-starting listening —
      // this test drives listening manually to exercise the STT path.
      speak: vi.fn((text, callbacks) => callbacks?.onStopped?.()),
      stop: vi.fn(),
      dispose: vi.fn(),
    }
  }
  function makeFakeStt() {
    let lastCallbacks = null
    return {
      isSupported: true,
      start: vi.fn((callbacks) => {
        lastCallbacks = callbacks
      }),
      stop: vi.fn(),
      dispose: vi.fn(),
      _callbacks: () => lastCallbacks,
    }
  }
  return { fakeTts: makeFakeTts(), fakeStt: makeFakeStt() }
})

vi.mock('../api/interviews.js', () => ({
  getInterview: vi.fn(),
  startInterview: vi.fn(),
  submitInterviewAnswer: vi.fn(),
}))
vi.mock('../voice/providers/index.js', () => ({
  createVoiceProviders: () => ({ tts: fakeTts, stt: fakeStt }),
}))

import { getInterview, startInterview, submitInterviewAnswer } from '../api/interviews.js'
import Interview from './Interview.jsx'

const QUESTION_TEXT = 'Explain how a Redis distributed lock works.'

function renderInterview() {
  return render(
    <MemoryRouter initialEntries={['/interview/session-1']}>
      <Routes>
        <Route path="/interview/:sessionId" element={<Interview />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('remote STT integration: VoiceInterviewView -> useVoiceInterviewSession -> remoteSttProvider -> answer state', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getInterview.mockResolvedValue({ status: 'CREATED', role: 'ai-engineer', difficulty: 'medium', question_limit: 4 })
    startInterview.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q1', sequence: 1, text: QUESTION_TEXT, topic: 'llm' },
    })
    submitInterviewAnswer.mockResolvedValue({})
  })

  afterEach(() => {
    cleanup()
  })

  async function enterVoiceMode() {
    renderInterview()
    await waitFor(() => expect(screen.getByText(QUESTION_TEXT)).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /Voice mode/ }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Speak answer' })).toBeTruthy())
  }

  it('interim and final transcripts from the remote provider reach the answer textarea, and manual submission uses the existing API', async () => {
    await enterVoiceMode()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    expect(fakeStt.start).toHaveBeenCalledOnce()
    const callbacks = fakeStt._callbacks()

    callbacks.onStart()
    callbacks.onSpeechDetected()
    callbacks.onInterim('I would first')

    // Interim text is not yet committed to the answer — only finals are.
    expect(screen.getByLabelText('Your answer').value).toBe('')

    callbacks.onFinal('I would first check the lock TTL.')
    await waitFor(() => expect(screen.getByLabelText('Your answer').value).toBe('I would first check the lock TTL.'))

    // STT never submits by itself.
    expect(submitInterviewAnswer).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }))
    await waitFor(() => expect(submitInterviewAnswer).toHaveBeenCalledOnce())
    expect(submitInterviewAnswer).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({ questionId: 'q1', answer: 'I would first check the lock TTL.' }),
    )
  })

  it('multiple final chunks within one listening session accumulate into the same answer', async () => {
    await enterVoiceMode()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()

    callbacks.onFinal('First, I would check')
    await waitFor(() => expect(screen.getByLabelText('Your answer').value).toBe('First, I would check'))

    callbacks.onFinal('the TTL on the lock key.')
    await waitFor(() =>
      expect(screen.getByLabelText('Your answer').value).toBe('First, I would check the TTL on the lock key.'),
    )
  })

  it('manually editing the transcript is preserved — a later final chunk appends rather than overwriting it', async () => {
    await enterVoiceMode()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()

    callbacks.onFinal('Redis SETNX')
    await waitFor(() => expect(screen.getByLabelText('Your answer').value).toBe('Redis SETNX'))

    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'Redis SETNX with a TTL' } })
    expect(screen.getByLabelText('Your answer').value).toBe('Redis SETNX with a TTL')

    callbacks.onFinal('implements the lock.')
    await waitFor(() =>
      expect(screen.getByLabelText('Your answer').value).toBe('Redis SETNX with a TTL implements the lock.'),
    )
  })

  it('an explicit stop ends listening without submitting or fabricating an answer', async () => {
    await enterVoiceMode()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onStart()

    // providers.stt.stop() is legitimately already called a couple of times
    // by ordinary component lifecycle before this point — once from the
    // mount-time "not active yet" guard (phase starts as 'loading'), once
    // from the initial question load being treated as a question change
    // (see useVoiceInterviewSession's resetForQuestion effect). Neither is
    // related to this click, so the click's own effect is asserted as a
    // delta, not an absolute call count.
    const stopCallsBeforeClick = fakeStt.stop.mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    expect(fakeStt.stop.mock.calls.length).toBe(stopCallsBeforeClick + 1)

    callbacks.onStopped()

    expect(screen.getByLabelText('Your answer').value).toBe('')
    expect(submitInterviewAnswer).not.toHaveBeenCalled()
  })

  it('voice mode can return to text mode safely after a transcript was captured', async () => {
    await enterVoiceMode()
    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    fakeStt._callbacks().onFinal('captured answer')
    await waitFor(() => expect(screen.getByLabelText('Your answer').value).toBe('captured answer'))

    fireEvent.click(screen.getByRole('button', { name: 'Switch to text' }))

    await waitFor(() => expect(screen.getByPlaceholderText('Explain your approach, reasoning, and trade-offs...')).toBeTruthy())
    expect(screen.getByPlaceholderText('Explain your approach, reasoning, and trade-offs...').value).toBe('captured answer')
  })
})
