// @vitest-environment jsdom
//
// The complete application path with a mocked remote STT provider,
// exercising the REAL useVoiceInterviewSession hook and voiceReducer. Only
// the provider factory is faked, matching how remote mode is actually
// selected in production (VITE_STT_MODE=remote just swaps which object
// createVoiceProviders() returns) — VoiceInterviewView,
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
      // automatic question-speech effect gets out of the way without ever
      // locking the mic to the speaker or auto-starting listening — this
      // test drives listening manually to exercise the STT path.
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
      // Mirrors the real provider's eventual settling: stop() ends the
      // attempt and fires its own onStopped — never a fabricated final
      // transcript. Finish Answer (see Interview.jsx's finishListening
      // orchestration) awaits this before submitting, so it must actually
      // resolve for those tests to reach submitInterviewAnswer at all.
      stop: vi.fn(() => {
        lastCallbacks?.onStopped?.()
      }),
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

  // Voice is the interview — the room (and its "Speak answer" control) is
  // present as soon as the interview is ready, with no mode toggle to click.
  async function renderReadyInterview() {
    renderInterview()
    await waitFor(() => expect(screen.getByText(QUESTION_TEXT)).toBeTruthy())
    await waitFor(() => expect(screen.getByRole('button', { name: 'Speak answer' })).toBeTruthy())
  }

  it('interim and final transcripts from the remote provider reach the read-only answer display, and manual submission uses the existing API', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    expect(fakeStt.start).toHaveBeenCalledOnce()
    const callbacks = fakeStt._callbacks()

    callbacks.onStart()
    callbacks.onSpeechDetected()
    callbacks.onInterim('I would first')

    // Interim text is not yet committed to the answer — only finals are.
    expect(screen.getByLabelText('Your answer').textContent).toBe('')

    callbacks.onFinal('I would first check the lock TTL.')
    await waitFor(() => expect(screen.getByLabelText('Your answer').textContent).toBe('I would first check the lock TTL.'))

    // STT never submits by itself.
    expect(submitInterviewAnswer).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Finish Answer' }))
    await waitFor(() => expect(submitInterviewAnswer).toHaveBeenCalledOnce())
    expect(submitInterviewAnswer).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({ questionId: 'q1', answer: 'I would first check the lock TTL.' }),
    )
  })

  it('multiple final chunks within one listening session accumulate into the same answer', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()

    callbacks.onFinal('First, I would check')
    await waitFor(() => expect(screen.getByLabelText('Your answer').textContent).toBe('First, I would check'))

    callbacks.onFinal('the TTL on the lock key.')
    await waitFor(() =>
      expect(screen.getByLabelText('Your answer').textContent).toBe('First, I would check the TTL on the lock key.'),
    )
  })

  // "Manually editing the transcript" is no longer a real scenario — the
  // answer display is read-only captions now (no textarea, no typed
  // fallback), so there is nothing for a candidate to edit. Coverage for
  // "a later final chunk appends rather than overwrites" already exists
  // above ('multiple final chunks within one listening session
  // accumulate into the same answer').

  it('an explicit stop ends listening without submitting or fabricating an answer', async () => {
    await renderReadyInterview()

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
    // The fake's stop() already fires onStopped synchronously (mirroring
    // the real provider's eventual settling) — no separate manual trigger
    // needed here.

    expect(screen.getByLabelText('Your answer').textContent).toBe('')
    expect(submitInterviewAnswer).not.toHaveBeenCalled()
  })

  // -------------------------------------------------------------------
  // Natural pause / Finish Answer semantics
  // -------------------------------------------------------------------

  it('1&2. a short pause (Deepgram UtteranceEnd) never submits, never starts evaluation, and the mic stays usable', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onSpeechDetected()
    callbacks.onFinal('I would use Redis for caching because')

    // "[pause]" — Deepgram's UtteranceEnd fires after ~1s of silence.
    callbacks.onSpeechEnd()

    expect(submitInterviewAnswer).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Evaluating your answer…' })).toBeNull()
    // The mic control is still the ordinary, clickable "listening" control —
    // never disabled/"Processing…" from a mere pause.
    expect(screen.getByRole('button', { name: 'Stop' })).toHaveProperty('disabled', false)
  })

  it('3. the candidate can keep talking after a pause, and Finish Answer submits the complete, combined answer exactly once', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onSpeechDetected()
    callbacks.onFinal('I would use Redis for caching because')
    await waitFor(() => expect(screen.getByLabelText('Your answer').textContent).toBe('I would use Redis for caching because'))
    callbacks.onSpeechEnd() // pause — must not end the attempt

    // "...and I would invalidate the cache when the underlying data changes."
    callbacks.onSpeechDetected()
    callbacks.onFinal('and I would invalidate the cache when the underlying data changes.')
    await waitFor(() =>
      expect(screen.getByLabelText('Your answer').textContent).toBe(
        'I would use Redis for caching because and I would invalidate the cache when the underlying data changes.',
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Finish Answer' }))
    await waitFor(() => expect(submitInterviewAnswer).toHaveBeenCalledOnce())
    expect(submitInterviewAnswer).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({
        answer: 'I would use Redis for caching because and I would invalidate the cache when the underlying data changes.',
      }),
    )
  })

  it('8. a final transcript that only arrives during the Finish Answer stop race is still included in what gets submitted', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onSpeechDetected()
    callbacks.onFinal('Redis uses SETNX with a TTL')
    await waitFor(() => expect(screen.getByLabelText('Your answer').textContent).toBe('Redis uses SETNX with a TTL'))

    // Deepgram is still finishing classification of the last bit of audio
    // when Finish Answer is clicked — its trailing final for that audio
    // arrives as part of the provider's own stop() settling, exactly as
    // remoteSttProvider.test.js's "10c" models at the provider level.
    fakeStt.stop.mockImplementationOnce(() => {
      callbacks.onFinal('for the lock.')
      callbacks.onStopped()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Finish Answer' }))
    await waitFor(() => expect(submitInterviewAnswer).toHaveBeenCalledOnce())
    expect(submitInterviewAnswer).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({ answer: 'Redis uses SETNX with a TTL for the lock.' }),
    )
  })

  it('9. clicking Finish Answer without ever having spoken or typed anything submits nothing', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onStart()

    // The button is disabled while the answer is empty, matching the
    // existing canSubmit gate — nothing to click through in the first
    // place, and no submission happens regardless.
    expect(screen.getByRole('button', { name: 'Finish Answer' })).toHaveProperty('disabled', true)
    fireEvent.click(screen.getByRole('button', { name: 'Finish Answer' }))

    expect(submitInterviewAnswer).not.toHaveBeenCalled()
  })

  it('6. Finish Answer submits exactly once, even if the button is clicked again while it is settling', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onFinal('A complete answer.')
    await waitFor(() => expect(screen.getByLabelText('Your answer').textContent).toBe('A complete answer.'))

    const finishButton = screen.getByRole('button', { name: 'Finish Answer' })
    fireEvent.click(finishButton)
    // The button is already busy/disabled the instant the first click is
    // handled — a rapid second click has nothing to act on.
    fireEvent.click(finishButton)
    fireEvent.click(finishButton)

    await waitFor(() => expect(submitInterviewAnswer).toHaveBeenCalledOnce())
  })

  it('7. an interim transcript alone (never finalized) is never submitted', async () => {
    await renderReadyInterview()

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onSpeechDetected()
    callbacks.onInterim('I would use Red')

    // Nothing has been finalized yet, so there is no committed answer to
    // submit — the control reflects that rather than acting on interim text.
    expect(screen.getByLabelText('Your answer').textContent).toBe('')
    expect(screen.getByRole('button', { name: 'Finish Answer' })).toHaveProperty('disabled', true)
    expect(submitInterviewAnswer).not.toHaveBeenCalled()
  })

  it('10. Replay question still works after a Finish Answer cycle', async () => {
    await renderReadyInterview()
    submitInterviewAnswer.mockResolvedValue({
      status: 'IN_PROGRESS',
      question: { id: 'q2', sequence: 2, text: 'A follow-up question.', topic: 'llm' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    const callbacks = fakeStt._callbacks()
    callbacks.onFinal('An answer to the first question.')
    await waitFor(() => expect(screen.getByLabelText('Your answer').textContent).toBe('An answer to the first question.'))

    fireEvent.click(screen.getByRole('button', { name: 'Finish Answer' }))
    await waitFor(() => expect(screen.getByText('A follow-up question.')).toBeTruthy())

    const speakCallsBeforeReplay = fakeTts.speak.mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Replay question' }))
    expect(fakeTts.speak.mock.calls.length).toBe(speakCallsBeforeReplay + 1)
    expect(fakeTts.speak).toHaveBeenLastCalledWith('A follow-up question.', expect.anything())
  })
})
