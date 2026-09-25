// @vitest-environment jsdom
//
// Focused coverage for:
//   1. The PROCESSING-timeout recovery mechanism. PROCESSING is now only
//      ever entered by an explicit commands.finishListening() call (the
//      candidate's Finish Answer) — never by a Deepgram UtteranceEnd/pause
//      (see voiceReducer.js's FINISH_REQUESTED vs. its now-harmless
//      STT_SPEECH_ENDED). finishListening() itself already calls
//      providers.stt.stop(); if that never resolves (the provider's own
//      graceful-stop grace period somehow never settles), this hook gives
//      up waiting after PROCESSING_TIMEOUT_MS and retries stop() once more
//      — nothing here invents a transcript or submits anything (this hook
//      has no submit concept at all; submission lives in Interview.jsx,
//      entirely outside it).
//   2. Natural pause handling: a Deepgram UtteranceEnd during CANDIDATE_
//      SPEAKING must never disable the mic or end the listening attempt —
//      the candidate must be able to keep talking after a pause.
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
// automatic path (auto-speak -> auto-listen -> speech detected -> Finish
// Answer), exactly as a real TTS-finishes-then-candidate-speaks-then-
// finishes turn would. The fake stt.stop() is a no-op by default in this
// describe block (see beforeEach), so the finishListening()-triggered
// stop() call this performs does NOT resolve on its own — tests that need
// it to eventually resolve arrange that explicitly.
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
    hook.result.current.commands.finishListening()
  })

  expect(hook.result.current.state.status).toBe(VOICE_STATUS.PROCESSING)
  return hook
}

describe('useVoiceInterviewSession PROCESSING-timeout recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    // Overrides the module-level fake's default auto-firing stop() (see
    // its own comment) — these tests need to actually hold PROCESSING so
    // there is something for the outer recovery timeout to recover from.
    fakeStt.stop.mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
    // Restores the module-level fake's default auto-firing stop() so this
    // block's override never leaks into a later describe block's tests.
    fakeStt.stop.mockImplementation(() => {
      fakeStt._callbacks()?.onStopped?.()
    })
  })

  it('1. finishListening() enters PROCESSING and calls stop() on the provider', () => {
    const { result } = renderAndReachProcessing()
    expect(result.current.state.status).toBe(VOICE_STATUS.PROCESSING)
    expect(result.current.micUiState).toBe('processing')
    expect(fakeStt.stop).toHaveBeenCalledTimes(1)
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
    // The timeout's own retry is what actually gets a response this time —
    // simulating the underlying connection settling only once nudged again.
    fakeStt.stop.mockImplementation(() => fakeStt._callbacks()?.onStopped?.())

    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS)
    })

    expect(fakeStt.stop).toHaveBeenCalledTimes(2) // the initial finishListening() call, then the timeout's retry
    // Recovery lands on IDLE — an already-supported rest state ("Speak
    // answer" becomes available again), never a new/invented UX state.
    expect(result.current.state.status).toBe(VOICE_STATUS.IDLE)
    expect(result.current.micUiState).toBe('idle')
  })

  it('4. the timeout never submits an answer — it only retries stopping the stalled provider, nothing else', () => {
    const onTranscript = vi.fn()
    renderAndReachProcessing({ onTranscript })
    fakeStt.stop.mockImplementation(() => fakeStt._callbacks()?.onStopped?.())

    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS)
    })

    // No transcript was ever finalized in this attempt, so nothing is
    // delivered to the caller (which is what Interview.jsx would submit) —
    // the timeout must never fabricate one.
    expect(onTranscript).not.toHaveBeenCalled()
    // Exactly two stop() calls total: finishListening()'s own, then the
    // timeout's single retry; nothing resembling a submit command exists
    // on this hook at all.
    expect(fakeStt.stop).toHaveBeenCalledTimes(2)
  })

  it('5. an already-captured final transcript survives the timeout recovery untouched', () => {
    const hook = renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true },
    })
    act(() => {
      fakeTts._callbacks().onNaturalEnd()
    })

    // A first chunk arrives and is captured (back to CANDIDATE_LISTENING,
    // per STT_FINAL's own contract) — the candidate paused, then resumed
    // and finished — before the provider goes silent and never actually
    // stops on its own.
    act(() => {
      fakeStt._callbacks().onFinal('Redis uses SETNX with a TTL')
    })
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    act(() => {
      hook.result.current.commands.finishListening()
    })
    expect(hook.result.current.state.status).toBe(VOICE_STATUS.PROCESSING)
    expect(hook.result.current.state.finalTranscript).toBe('Redis uses SETNX with a TTL')
    const seqBeforeTimeout = hook.result.current.state.finalTranscriptSeq

    fakeStt.stop.mockImplementation(() => fakeStt._callbacks()?.onStopped?.())
    act(() => {
      vi.advanceTimersByTime(PROCESSING_TIMEOUT_MS)
    })

    expect(hook.result.current.state.status).toBe(VOICE_STATUS.IDLE)
    // The recovery path (STT_STOPPED) never touches finalTranscript/seq.
    expect(hook.result.current.state.finalTranscript).toBe('Redis uses SETNX with a TTL')
    expect(hook.result.current.state.finalTranscriptSeq).toBe(seqBeforeTimeout)
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

// Natural pause handling: a Deepgram UtteranceEnd (fired after every ~1s of
// silence — see remoteSttProvider.js's UTTERANCE_END_MS) must never be
// treated as "the candidate is done." It only means the current speech
// segment finalized; the mic must stay open and usable so the candidate can
// keep talking, exactly like a human interviewer waiting through a pause.
describe('useVoiceInterviewSession natural pause handling (Deepgram UtteranceEnd)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function renderListening(props = {}) {
    const hook = renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true, ...props },
    })
    act(() => {
      fakeTts._callbacks().onNaturalEnd()
    })
    return hook
  }

  it('1&2. a short pause (UtteranceEnd) never enters PROCESSING and never calls stop()', () => {
    const hook = renderListening()
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })

    act(() => {
      fakeStt._callbacks().onSpeechEnd()
    })

    expect(hook.result.current.state.status).not.toBe(VOICE_STATUS.PROCESSING)
    expect(hook.result.current.micUiState).not.toBe('processing')
    expect(fakeStt.stop).not.toHaveBeenCalled()
  })

  it('a pause returns the room to "listening", not stuck on "hearing you"', () => {
    const hook = renderListening()
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    expect(hook.result.current.state.status).toBe(VOICE_STATUS.CANDIDATE_SPEAKING)

    act(() => {
      fakeStt._callbacks().onSpeechEnd()
    })

    expect(hook.result.current.state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)
    expect(hook.result.current.micUiState).toBe('listening')
  })

  it('3. the candidate can resume speaking after a pause — SpeechStarted after UtteranceEnd still registers', () => {
    const hook = renderListening()
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    act(() => {
      fakeStt._callbacks().onSpeechEnd()
    })
    expect(hook.result.current.state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)

    // "...and I'd invalidate the cache when..." — resumed after the pause.
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })

    expect(hook.result.current.state.status).toBe(VOICE_STATUS.CANDIDATE_SPEAKING)
  })

  it('4. multiple final segments across a pause are each captured, and the mic never had to be manually restarted', () => {
    const hook = renderListening()

    // "I would use Redis for caching because..."
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    act(() => {
      fakeStt._callbacks().onFinal('I would use Redis for caching because')
    })
    expect(hook.result.current.state.finalTranscript).toBe('I would use Redis for caching because')

    // [pause — UtteranceEnd fires, nothing here submits or stops anything]
    act(() => {
      fakeStt._callbacks().onSpeechEnd()
    })
    expect(fakeStt.stop).not.toHaveBeenCalled()
    expect(hook.result.current.state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)

    // "...and I would invalidate the cache when..." — same attempt, no
    // restart, no new start() call was ever needed.
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    act(() => {
      fakeStt._callbacks().onFinal('and I would invalidate the cache when the underlying data changes.')
    })

    expect(hook.result.current.state.finalTranscript).toBe('and I would invalidate the cache when the underlying data changes.')
    expect(fakeStt.start).toHaveBeenCalledTimes(1) // one continuous attempt throughout
  })

  it('a stale UtteranceEnd from a superseded attempt is ignored', () => {
    const hook = renderListening()
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    const staleCallbacks = fakeStt._callbacks()

    // The question changes mid-answer — a new attempt supersedes this one.
    act(() => {
      hook.rerender({ questionId: 'q2', questionText: 'A different question.', active: true })
    })

    act(() => {
      staleCallbacks.onSpeechEnd()
    })

    // Nothing about the new attempt/question is disturbed by the stale event.
    expect(hook.result.current.state.status).not.toBe(VOICE_STATUS.PROCESSING)
  })
})

// commands.finishListening() / the Finish Answer control's STT-side
// semantics: the ONLY thing allowed to move a busy mic into PROCESSING, and
// the one path that ends a listening attempt on the candidate's explicit
// request rather than an automatic silence signal.
describe('useVoiceInterviewSession finishListening (Finish Answer)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function renderListeningAndSpeaking() {
    const hook = renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true },
    })
    act(() => {
      fakeTts._callbacks().onNaturalEnd()
    })
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })
    return hook
  }

  it('does nothing (and calls stop() zero times) when the mic was never active', () => {
    const hook = renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true },
    })
    // TTS never even settled — the mic was never opened this turn.
    act(() => {
      hook.result.current.commands.finishListening()
    })

    expect(fakeStt.stop).not.toHaveBeenCalled()
    expect(hook.result.current.state.status).not.toBe(VOICE_STATUS.PROCESSING)
  })

  it('5&6. enters PROCESSING, stops the provider exactly once, and settles back to IDLE', async () => {
    const hook = renderListeningAndSpeaking()
    // Held open deliberately (rather than the module default's synchronous
    // auto-resolve) so PROCESSING is actually observable before settling —
    // modeling the real provider's short grace period.
    let resolveStop
    fakeStt.stop.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveStop = resolve
        }),
    )

    let finished
    act(() => {
      finished = hook.result.current.commands.finishListening()
    })
    expect(hook.result.current.state.status).toBe(VOICE_STATUS.PROCESSING)
    expect(fakeStt.stop).toHaveBeenCalledTimes(1)

    await act(async () => {
      fakeStt._callbacks().onStopped()
      resolveStop()
      await finished
    })

    expect(hook.result.current.state.status).toBe(VOICE_STATUS.IDLE)
    // A second, redundant finishListening() call while already at rest
    // must not call stop() again — exactly one stop per finish request.
    await act(async () => {
      await hook.result.current.commands.finishListening()
    })
    expect(fakeStt.stop).toHaveBeenCalledTimes(1)
  })

  it('7. an interim transcript is cleared on finish and never delivered as a final', () => {
    const hook = renderListeningAndSpeaking()
    act(() => {
      fakeStt._callbacks().onInterim('I would use Red')
    })
    expect(hook.result.current.state.interimTranscript).toBe('I would use Red')

    act(() => {
      hook.result.current.commands.finishListening()
    })

    expect(hook.result.current.state.interimTranscript).toBe('')
  })

  it('8. a final transcript delivered during the finish/stop window is still captured, not lost', async () => {
    const onTranscript = vi.fn()
    const hook = renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true, onTranscript },
    })
    act(() => {
      fakeTts._callbacks().onNaturalEnd()
    })
    act(() => {
      fakeStt._callbacks().onSpeechDetected()
    })

    // The fake's stop() only fires onStopped — a race where Deepgram's
    // trailing final for audio already sent arrives in between is modeled
    // by delivering it first, then letting stop() settle, exactly as
    // remoteSttProvider.test.js verifies at the provider level.
    fakeStt.stop.mockImplementationOnce(() => {
      fakeStt._callbacks().onFinal('the trailing words just before the click')
      fakeStt._callbacks().onStopped()
    })

    let finished
    act(() => {
      finished = hook.result.current.commands.finishListening()
    })
    await act(async () => {
      await finished
    })

    expect(hook.result.current.state.finalTranscript).toBe('the trailing words just before the click')
    expect(onTranscript).toHaveBeenCalledWith('the trailing words just before the click')
    expect(hook.result.current.state.status).toBe(VOICE_STATUS.IDLE)
  })

  it('a stale finishListening() attemptId can never move a newer attempt into PROCESSING', () => {
    const hook = renderListeningAndSpeaking()
    const finishForFirstAttempt = hook.result.current.commands.finishListening

    // A question change supersedes the attempt before finish actually runs.
    act(() => {
      hook.rerender({ questionId: 'q2', questionText: 'A different question.', active: true })
    })
    act(() => {
      fakeTts._callbacks().onNaturalEnd()
    })

    act(() => {
      finishForFirstAttempt()
    })

    expect(hook.result.current.state.status).not.toBe(VOICE_STATUS.PROCESSING)
  })
})

// Focused coverage for combining `questionLeadIn` (the interviewer's short
// conversational reaction) with `questionText` into the single spoken turn.
// The combining itself (null/empty/whitespace safety, no double-speaking) is
// unit-tested directly against buildSpokenQuestion in speechPresentation.test.js
// — this only verifies the hook actually wires it in as exactly one speak() call.
describe('useVoiceInterviewSession lead-in + question combined speech', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('speaks lead-in and question as one combined utterance, in exactly one TTS call', () => {
    renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: {
        questionId: 'q1',
        questionText: 'How would you handle cache invalidation in a distributed system?',
        questionLeadIn: "That's interesting. You mentioned cache invalidation.",
        active: true,
      },
    })

    expect(fakeTts.speak).toHaveBeenCalledTimes(1)
    expect(fakeTts.speak).toHaveBeenCalledWith(
      "That's interesting. You mentioned cache invalidation. How would you handle cache invalidation in a distributed system?",
      expect.anything(),
    )
  })

  it('speaks only the question when there is no lead-in (null)', () => {
    renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, questionLeadIn: null, active: true },
    })

    expect(fakeTts.speak).toHaveBeenCalledTimes(1)
    expect(fakeTts.speak).toHaveBeenCalledWith(QUESTION_TEXT, expect.anything())
  })

  it('speaks only the question when questionLeadIn is omitted entirely', () => {
    renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, active: true },
    })

    expect(fakeTts.speak).toHaveBeenCalledTimes(1)
    expect(fakeTts.speak).toHaveBeenCalledWith(QUESTION_TEXT, expect.anything())
  })

  it('speaks only the question when questionLeadIn is whitespace-only', () => {
    renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: { questionId: 'q1', questionText: QUESTION_TEXT, questionLeadIn: '   ', active: true },
    })

    expect(fakeTts.speak).toHaveBeenCalledTimes(1)
    expect(fakeTts.speak).toHaveBeenCalledWith(QUESTION_TEXT, expect.anything())
  })

  it('a manual replay speaks the same combined text as the automatic turn, still one call each time', () => {
    const hook = renderHook((p) => useVoiceInterviewSession(p), {
      initialProps: {
        questionId: 'q1',
        questionText: QUESTION_TEXT,
        questionLeadIn: 'Good, let’s dig into that.',
        active: true,
      },
    })

    expect(fakeTts.speak).toHaveBeenCalledTimes(1)

    act(() => {
      hook.result.current.commands.replayQuestion()
    })

    expect(fakeTts.speak).toHaveBeenCalledTimes(2)
    expect(fakeTts.speak).toHaveBeenNthCalledWith(
      2,
      `Good, let’s dig into that. ${QUESTION_TEXT}`,
      expect.anything(),
    )
  })
})
