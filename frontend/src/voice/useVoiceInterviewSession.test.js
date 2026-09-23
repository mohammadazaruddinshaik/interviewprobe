// @vitest-environment jsdom
//
// Focused coverage for the PROCESSING-timeout recovery mechanism in
// useVoiceInterviewSession.js: normally STT_SPEECH_ENDED (Deepgram's
// UtteranceEnd) is followed shortly by either another STT_FINAL or an
// STT_STOPPED/STT_ERROR (see voiceReducer.js). If neither ever arrives, the
// hook now gives up waiting after PROCESSING_TIMEOUT_MS and recovers on its
// own by stopping the (apparently stalled) provider — the exact same path a
// manual stop takes, so nothing here invents a transcript or submits
// anything (this hook has no submit concept at all; submission lives in
// Interview.jsx, entirely outside it).
//
// Only the provider factory is faked — the real reducer and the real
// attempt-id race protection run throughout, matching the pattern already
// used by Interview.remoteStt.integration.test.jsx.
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PROCESSING_TIMEOUT_MS, useVoiceInterviewSession } from './useVoiceInterviewSession.js'
import { VOICE_STATUS } from './voiceState.js'

const { fakeTts, fakeStt } = vi.hoisted(() => {
  function makeFakeTts() {
    let lastCallbacks = null
    return {
      isSupported: true,
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
      // Mirrors the real providers: stop() tears the attempt down and fires
      // its own onStopped callback — never a fabricated final transcript.
      stop: vi.fn(() => {
        lastCallbacks?.onStopped?.()
      }),
      dispose: vi.fn(),
      _callbacks: () => lastCallbacks,
    }
  }
  return { fakeTts: makeFakeTts(), fakeStt: makeFakeStt() }
})

vi.mock('./providers/index.js', () => ({
  createVoiceProviders: () => ({ tts: fakeTts, stt: fakeStt }),
}))

const QUESTION_TEXT = 'Explain how a Redis distributed lock works.'

// Drives a freshly rendered hook all the way to PROCESSING via the normal
// automatic path (auto-speak -> auto-listen -> speech detected -> speech
// ended), exactly as a real TTS-finishes-then-candidate-speaks turn would.
function renderAndReachProcessing(props = {}) {
  const hook = renderHook((p) => useVoiceInterviewSession(p), {
    initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true, ...props },
  })

  act(() => {
    fakeTts._callbacks().onNaturalEnd()
  })
  act(() => {
    fakeStt._callbacks().onSpeechDetected()
  })
  act(() => {
    fakeStt._callbacks().onSpeechEnd()
  })

  expect(hook.result.current.state.status).toBe(VOICE_STATUS.PROCESSING)
  return hook
}

describe('useVoiceInterviewSession PROCESSING-timeout recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('1. STT_SPEECH_ENDED (UtteranceEnd) enters PROCESSING', () => {
    const { result } = renderAndReachProcessing()
    expect(result.current.state.status).toBe(VOICE_STATUS.PROCESSING)
    expect(result.current.micUiState).toBe('processing')
  })

  it('2. an expected final transcript resolves PROCESSING normally, without the timeout ever firing', () => {
    const { result } = renderAndReachProcessing()
    const sttStopCallsBeforeFinal = fakeStt.stop.mock.calls.length

    act(() => {
      fakeStt._callbacks().onFinal('Redis uses SETNX with a TTL for the lock.')
    })

    expect(result.current.state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)
    expect(result.current.state.finalTranscript).toBe('Redis uses SETNX with a TTL for the lock.')

    // The PROCESSING effect's own cleanup must have cancelled the pending
    // timer the moment status left PROCESSING — advancing well past the
    // timeout must not produce a late, spurious stop() call.
    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS * 2)
    })
    expect(fakeStt.stop.mock.calls.length).toBe(sttStopCallsBeforeFinal)
  })

  it('3. PROCESSING recovers on its own once the timeout elapses with no further event', () => {
    const { result } = renderAndReachProcessing()

    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS)
    })

    expect(fakeStt.stop).toHaveBeenCalled()
    // Recovery lands on IDLE — an already-supported rest state ("Speak
    // answer" becomes available again), never a new/invented UX state.
    expect(result.current.state.status).toBe(VOICE_STATUS.IDLE)
    expect(result.current.micUiState).toBe('idle')
  })

  it('4. the timeout never submits an answer — it only stops the stalled provider, nothing else', () => {
    const onTranscript = vi.fn()
    renderAndReachProcessing({ onTranscript })

    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS)
    })

    // No transcript was ever finalized in this attempt, so nothing is
    // delivered to the caller (which is what Interview.jsx would submit) —
    // the timeout must never fabricate one.
    expect(onTranscript).not.toHaveBeenCalled()
    // The only side effect is stopping the provider; nothing resembling a
    // submit command exists on this hook at all.
    expect(fakeStt.stop).toHaveBeenCalledTimes(1)
  })

  it('5. an already-captured final transcript survives the timeout recovery untouched', () => {
    const { result } = renderAndReachProcessing()

    // A first chunk arrives and is captured (back to CANDIDATE_LISTENING,
    // per STT_FINAL's own contract), then the provider goes silent and a
    // second UtteranceEnd is never followed by anything further.
    act(() => {
      fakeStt._callbacks().onFinal('Redis uses SETNX with a TTL')
    })
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    act(() => {
      fakeStt._callbacks().onSpeechEnd()
    })
    expect(result.current.state.status).toBe(VOICE_STATUS.PROCESSING)
    expect(result.current.state.finalTranscript).toBe('Redis uses SETNX with a TTL')
    const seqBeforeTimeout = result.current.state.finalTranscriptSeq

    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS)
    })

    expect(result.current.state.status).toBe(VOICE_STATUS.IDLE)
    // The recovery path (STT_STOPPED) never touches finalTranscript/seq.
    expect(result.current.state.finalTranscript).toBe('Redis uses SETNX with a TTL')
    expect(result.current.state.finalTranscriptSeq).toBe(seqBeforeTimeout)
  })

  it('6. a stale timeout from a previous question never affects a newer question/attempt', () => {
    const { result, rerender } = renderAndReachProcessing()
    const sttStopCallsAtProcessing = fakeStt.stop.mock.calls.length

    // The question changes well before the first attempt's timeout would
    // fire — resetForQuestion bumps sttAttemptId and stops the old attempt
    // itself (a real, explicit stop, not the timeout's).
    act(() => {
      rerender({ questionId: 'q2', questionText: 'A different question entirely.', active: true })
    })
    const sttStopCallsAfterQuestionChange = fakeStt.stop.mock.calls.length
    expect(sttStopCallsAfterQuestionChange).toBeGreaterThan(sttStopCallsAtProcessing)
    // QUESTION_CHANGED resets to IDLE, and the new question's own
    // auto-speak effect fires immediately from there (the normal, desired
    // flow) — by the time this settles, TTS is already speaking again.
    expect(result.current.state.status).toBe(VOICE_STATUS.INTERVIEWER_SPEAKING)

    // Advance well past the ORIGINAL attempt's timeout — its timer must
    // have been cancelled by the question-change effect's own cleanup, so
    // this must not produce any further stop() call.
    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS * 2)
    })
    expect(fakeStt.stop.mock.calls.length).toBe(sttStopCallsAfterQuestionChange)

    // The new question's own automatic turn proceeds normally afterward,
    // undisturbed by the old attempt's expired timer.
    expect(fakeTts.speak).toHaveBeenCalledWith('A different question entirely.', expect.anything())
  })

  it('7. unmounting cleans up the pending timer — no state update or provider call fires after unmount', () => {
    const { unmount } = renderAndReachProcessing()
    const sttStopCallsBeforeUnmount = fakeStt.stop.mock.calls.length

    unmount()

    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS * 2)
    })

    // stop() (the timeout's own action) must not have fired post-unmount —
    // distinct from dispose(), which the unmount effect calls separately.
    expect(fakeStt.stop.mock.calls.length).toBe(sttStopCallsBeforeUnmount)
    expect(fakeStt.dispose).toHaveBeenCalled()
  })

  it('8. a normal fast turn (TTS -> listen -> speech -> final -> stop) is unaffected by the new timeout', () => {
    const hook = renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true },
    })

    act(() => {
      fakeTts._callbacks().onNaturalEnd()
    })
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    act(() => {
      fakeStt._callbacks().onFinal('A complete answer given without any pause.')
    })
    act(() => {
      fakeStt._callbacks().onStopped()
    })

    expect(hook.result.current.state.status).toBe(VOICE_STATUS.IDLE)
    expect(hook.result.current.state.finalTranscript).toBe('A complete answer given without any pause.')
    const sttStopCallsSoFar = fakeStt.stop.mock.calls.length

    // PROCESSING was never entered in this turn, so there is nothing for
    // the timeout effect to have scheduled — advancing time must be a
    // complete no-op.
    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS * 2)
    })
    expect(fakeStt.stop.mock.calls.length).toBe(sttStopCallsSoFar)
    expect(hook.result.current.state.status).toBe(VOICE_STATUS.IDLE)
  })
})
