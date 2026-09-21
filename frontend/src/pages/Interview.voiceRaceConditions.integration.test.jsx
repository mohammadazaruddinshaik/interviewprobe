// @vitest-environment jsdom
//
// Task 43 — hardening/production-QA. Exercises the REAL
// useVoiceInterviewSession hook and voiceReducer (only the provider factory
// is faked, same pattern as Interview.remoteStt.integration.test.jsx)
// through Interview.jsx, for race-condition scenarios not already covered
// at the reducer-unit or provider-unit level:
//
//   Case A — manual stop during automatic TTS must not auto-start the mic
//   Case C — disabling voice mode during TTS leaves no stale callback that
//            can start STT once it fires late
//   Case G — an STT error during a candidate response is recoverable,
//            never auto-submits, and never discards an already-accumulated
//            transcript
//
// Cases B/F (question-change invalidating TTS/STT attempts) and Case E
// (rapid replay never overlapping) are deliberately not re-tested here —
// they're already covered exhaustively at the reducer level
// (voiceReducer.test.js #8, #9, #12) and the provider level
// (remoteTtsProvider.test.js/remoteSttProvider.test.js "second call
// supersedes the first" / "stopping while still awaiting..." cases), and
// the UI structurally cannot fire two overlapping replay/listen clicks
// (each button toggles state synchronously on click, before a second click
// can land).
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { fakeTts, fakeStt } = vi.hoisted(() => {
  function makeFakeTts() {
    let lastCallbacks = null
    return {
      isSupported: true,
      // Unlike the STT integration test's fakeTts, this one does NOT
      // auto-resolve — callbacks are captured and fired manually so tests
      // can control exactly when (or whether) TTS "completes".
      speak: vi.fn((text, callbacks) => {
        lastCallbacks = callbacks
      }),
      stop: vi.fn(),
      dispose: vi.fn(),
      _callbacks: () => lastCallbacks,
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

async function enterVoiceMode() {
  renderInterview()
  await waitFor(() => expect(screen.getByText(QUESTION_TEXT)).toBeTruthy())
  fireEvent.click(screen.getByRole('button', { name: /Voice mode/ }))
  // Entering voice mode auto-speaks the question — wait for the speaker
  // button to flip into its "speaking" (Stop) state.
  await waitFor(() => expect(screen.getByRole('button', { name: 'Stop', hidden: true })).toBeTruthy())
}

describe('voice race conditions (real hook + real reducer, faked providers)', () => {
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

  it('Case A: manually stopping automatic TTS does not auto-start the microphone', async () => {
    await enterVoiceMode()
    const ttsCallbacks = fakeTts._callbacks()
    ttsCallbacks.onStart()

    // The speaker control is showing "Stop" (currently speaking) — click it
    // to stop manually, as a candidate interrupting the question mid-read.
    const speakerStopButtons = screen.getAllByRole('button', { name: 'Stop' })
    expect(speakerStopButtons).toHaveLength(1) // only the speaker is busy; mic isn't listening yet
    // providers.tts.stop() is legitimately already called by ordinary
    // component lifecycle before this point (the mount-time "not active
    // yet" guard, the initial question load's question-change reset) —
    // see the identical note in Interview.remoteStt.integration.test.jsx.
    // Asserted as a delta, not an absolute count.
    const stopCallsBeforeClick = fakeTts.stop.mock.calls.length
    fireEvent.click(speakerStopButtons[0])

    expect(fakeTts.stop.mock.calls.length).toBe(stopCallsBeforeClick + 1)

    // The provider's own onStopped (never onNaturalEnd) is what a real stop()
    // produces — simulate that arriving.
    ttsCallbacks.onStopped()

    // A manual stop must never be treated as natural completion: the mic
    // must not have been started automatically.
    expect(fakeStt.start).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Replay question' })).toBeTruthy())
  })

  it('Case C: disabling voice mode during TTS leaves no stale callback able to start STT', async () => {
    await enterVoiceMode()
    const ttsCallbacks = fakeTts._callbacks()
    ttsCallbacks.onStart()

    // Exit voice mode entirely while the question is still "speaking".
    fireEvent.click(screen.getByRole('button', { name: 'Switch to text' }))
    await waitFor(() =>
      expect(screen.getByPlaceholderText('Explain your approach, reasoning, and trade-offs...')).toBeTruthy(),
    )
    expect(fakeTts.stop).toHaveBeenCalled()

    // The original attempt's provider now fires its natural-end callback
    // late (a real race: the network/SDK callback was already in flight
    // when disableVoiceMode() ran). It must be a no-op — no stale mic start.
    ttsCallbacks.onNaturalEnd()

    expect(fakeStt.start).not.toHaveBeenCalled()
    // Still on the plain text UI — nothing about the mode was disturbed.
    expect(screen.getByPlaceholderText('Explain your approach, reasoning, and trade-offs...')).toBeTruthy()
  })

  it('Case G: an STT error during a candidate response is recoverable, preserves the transcript, and never auto-submits', async () => {
    await enterVoiceMode()
    fakeTts._callbacks().onStopped() // let the automatic question-speech settle out of the way

    fireEvent.click(await screen.findByRole('button', { name: 'Speak answer' }))
    const sttCallbacks = fakeStt._callbacks()
    sttCallbacks.onStart()
    sttCallbacks.onFinal('Redis uses SETNX with a TTL for the lock,')

    await waitFor(() => expect(screen.getByLabelText('Your answer').value).toBe('Redis uses SETNX with a TTL for the lock,'))

    // Recognition fails mid-response (e.g. a dropped connection). Fired
    // directly on the callback (not via fireEvent), so — same as the
    // provider-level tests — the resulting state update needs a `waitFor`
    // rather than a synchronous assertion for React to flush it.
    sttCallbacks.onError({ code: 'connection-lost', message: 'The voice input connection was lost. Please try again.', recoverable: true })

    // The error is surfaced and recoverable — a Dismiss control is offered.
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('The voice input connection was lost. Please try again.')
    // The already-accumulated transcript must survive the error untouched.
    expect(screen.getByLabelText('Your answer').value).toBe('Redis uses SETNX with a TTL for the lock,')
    // No automatic submission from an STT error.
    expect(submitInterviewAnswer).not.toHaveBeenCalled()
    const dismissButton = screen.getByRole('button', { name: 'Dismiss' })

    // The candidate can recover manually: dismiss, then submit the
    // preserved transcript through the ordinary (already-tested) path.
    fireEvent.click(dismissButton)
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }))
    await waitFor(() => expect(submitInterviewAnswer).toHaveBeenCalledOnce())
    expect(submitInterviewAnswer).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({ answer: 'Redis uses SETNX with a TTL for the lock,' }),
    )
  })
})
