import { describe, expect, it } from 'vitest'
import { VOICE_ACTION, voiceReducer } from './voiceReducer.js'
import { createInitialVoiceState, getActiveChannel, shouldAutoStartListening, VOICE_STATUS } from './voiceState.js'

function withVoiceMode(state = createInitialVoiceState()) {
  return voiceReducer(state, { type: VOICE_ACTION.VOICE_MODE_ENABLED })
}

describe('state transitions', () => {
  it('1. IDLE -> INTERVIEWER_SPEAKING on SPEAK_REQUESTED', () => {
    const idle = withVoiceMode()
    expect(idle.status).toBe(VOICE_STATUS.IDLE)

    const speaking = voiceReducer(idle, { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })

    expect(speaking.status).toBe(VOICE_STATUS.INTERVIEWER_SPEAKING)
    expect(speaking.isAutomaticSpeech).toBe(true)
    expect(getActiveChannel(speaking)).toBe('speaker')
  })

  it('2. INTERVIEWER_SPEAKING -> INTERVIEWER_FINISHED on TTS_NATURAL_END', () => {
    const speaking = voiceReducer(withVoiceMode(), { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })

    const finished = voiceReducer(speaking, { type: VOICE_ACTION.TTS_NATURAL_END, attemptId: 1 })

    expect(finished.status).toBe(VOICE_STATUS.INTERVIEWER_FINISHED)
  })

  it('3. INTERVIEWER_FINISHED -> CANDIDATE_LISTENING when the finished speech was automatic', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })
    state = voiceReducer(state, { type: VOICE_ACTION.TTS_NATURAL_END, attemptId: 1 })
    expect(state.status).toBe(VOICE_STATUS.INTERVIEWER_FINISHED)
    expect(shouldAutoStartListening(state)).toBe(true)

    // The session hook reacts to shouldAutoStartListening by issuing this
    // command; here we dispatch the resulting action directly.
    const listening = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: true, attemptId: 2 })

    expect(listening.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)
    expect(getActiveChannel(listening)).toBe('mic')
  })

  it('4. CANDIDATE_LISTENING -> CANDIDATE_SPEAKING on STT_SPEECH_DETECTED', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: false, attemptId: 1 })
    expect(state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)

    const speaking = voiceReducer(state, { type: VOICE_ACTION.STT_SPEECH_DETECTED, attemptId: 1 })

    expect(speaking.status).toBe(VOICE_STATUS.CANDIDATE_SPEAKING)
  })

  it('5. CANDIDATE_SPEAKING -> PROCESSING on STT_SPEECH_ENDED', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: false, attemptId: 1 })
    state = voiceReducer(state, { type: VOICE_ACTION.STT_SPEECH_DETECTED, attemptId: 1 })
    expect(state.status).toBe(VOICE_STATUS.CANDIDATE_SPEAKING)

    const processing = voiceReducer(state, { type: VOICE_ACTION.STT_SPEECH_ENDED, attemptId: 1 })

    expect(processing.status).toBe(VOICE_STATUS.PROCESSING)
    expect(getActiveChannel(processing)).toBe('mic') // still locked while finalizing
  })

  it('5b. STT_FINAL stays in CANDIDATE_LISTENING (mic still locked) rather than resting — a continuous-listening provider may still be capturing more speech', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: false, attemptId: 1 })
    state = voiceReducer(state, { type: VOICE_ACTION.STT_SPEECH_DETECTED, attemptId: 1 })

    const afterFinal = voiceReducer(state, { type: VOICE_ACTION.STT_FINAL, attemptId: 1, transcript: 'hello world' })

    expect(afterFinal.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)
    expect(getActiveChannel(afterFinal)).toBe('mic')
    expect(afterFinal.finalTranscript).toBe('hello world')
    expect(afterFinal.finalTranscriptSeq).toBe(1)
    expect(afterFinal.interimTranscript).toBe('')
  })

  it('5c. multiple STT_FINAL chunks within one attempt each bump finalTranscriptSeq and replace finalTranscript with just that chunk', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: false, attemptId: 1 })
    state = voiceReducer(state, { type: VOICE_ACTION.STT_FINAL, attemptId: 1, transcript: 'first chunk' })
    expect(state.finalTranscriptSeq).toBe(1)

    state = voiceReducer(state, { type: VOICE_ACTION.STT_SPEECH_DETECTED, attemptId: 1 })
    state = voiceReducer(state, { type: VOICE_ACTION.STT_FINAL, attemptId: 1, transcript: 'second chunk' })

    // Each STT_FINAL carries only its own delta — accumulation into a full
    // answer is the consumer's job (useVoiceInterviewSession's delivery
    // effect / Interview.jsx), never this reducer's.
    expect(state.finalTranscript).toBe('second chunk')
    expect(state.finalTranscriptSeq).toBe(2)
  })

  it('5d. STT_STOPPED after a final ends the attempt (mic released) — the only thing that does', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: false, attemptId: 1 })
    state = voiceReducer(state, { type: VOICE_ACTION.STT_FINAL, attemptId: 1, transcript: 'done' })
    expect(state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)

    const stopped = voiceReducer(state, { type: VOICE_ACTION.STT_STOPPED, attemptId: 1 })

    expect(stopped.status).toBe(VOICE_STATUS.IDLE)
    expect(getActiveChannel(stopped)).toBeNull()
    // The already-delivered seq/transcript are left untouched by stopping.
    expect(stopped.finalTranscriptSeq).toBe(1)
  })

  it('6. any lifecycle error -> ERROR, carrying the normalized error and its source', () => {
    const speaking = voiceReducer(withVoiceMode(), { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })
    const ttsErrored = voiceReducer(speaking, {
      type: VOICE_ACTION.TTS_ERROR,
      attemptId: 1,
      error: { code: 'synthesis-failed', message: 'boom', recoverable: true },
    })
    expect(ttsErrored.status).toBe(VOICE_STATUS.ERROR)
    expect(ttsErrored.error).toEqual({ code: 'synthesis-failed', message: 'boom', recoverable: true, source: 'tts' })

    const listening = voiceReducer(withVoiceMode(), { type: VOICE_ACTION.LISTEN_REQUESTED, auto: false, attemptId: 1 })
    const sttErrored = voiceReducer(listening, {
      type: VOICE_ACTION.STT_ERROR,
      attemptId: 1,
      error: { code: 'no-speech', message: 'nothing heard', recoverable: true },
    })
    expect(sttErrored.status).toBe(VOICE_STATUS.ERROR)
    expect(sttErrored.error.source).toBe('stt')
  })

  it('7. ERROR -> IDLE on CLEAR_ERROR (TEXT_MODE if voice mode is off)', () => {
    const errored = voiceReducer(withVoiceMode(), {
      type: VOICE_ACTION.STT_ERROR,
      attemptId: 0,
      error: { code: 'no-speech', message: 'x', recoverable: true },
    })
    expect(errored.status).toBe(VOICE_STATUS.ERROR)

    const cleared = voiceReducer(errored, { type: VOICE_ACTION.CLEAR_ERROR })
    expect(cleared.status).toBe(VOICE_STATUS.IDLE)
    expect(cleared.error).toBeNull()

    const erroredTextMode = voiceReducer(createInitialVoiceState(), {
      type: VOICE_ACTION.STT_ERROR,
      attemptId: 0,
      error: { code: 'no-speech', message: 'x', recoverable: true },
    })
    const clearedTextMode = voiceReducer(erroredTextMode, { type: VOICE_ACTION.CLEAR_ERROR })
    expect(clearedTextMode.status).toBe(VOICE_STATUS.TEXT_MODE)
  })
})

describe('race conditions', () => {
  it('8. a stale TTS completion cannot start STT for a newer question', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })
    expect(state.status).toBe(VOICE_STATUS.INTERVIEWER_SPEAKING)

    // The question changes mid-speech — this is what the session hook does
    // on a questionId change, before the old utterance's callback can fire.
    state = voiceReducer(state, { type: VOICE_ACTION.QUESTION_CHANGED, questionId: 'q2', attemptId: 2 })
    expect(state.status).toBe(VOICE_STATUS.IDLE)

    // The old (question 1) utterance's onend fires late, still carrying
    // attemptId 1.
    const afterStaleEvent = voiceReducer(state, { type: VOICE_ACTION.TTS_NATURAL_END, attemptId: 1 })

    expect(afterStaleEvent).toBe(state) // untouched — never reaches INTERVIEWER_FINISHED, never cascades into listening
    expect(afterStaleEvent.status).toBe(VOICE_STATUS.IDLE)
  })

  it('9. a cancelled TTS attempt never reaches INTERVIEWER_FINISHED, so it can never trigger automatic STT', () => {
    const speaking = voiceReducer(withVoiceMode(), { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })

    const stopped = voiceReducer(speaking, { type: VOICE_ACTION.TTS_STOPPED, attemptId: 1 })

    expect(stopped.status).toBe(VOICE_STATUS.IDLE) // straight back to rest
    expect(stopped.status).not.toBe(VOICE_STATUS.INTERVIEWER_FINISHED)
    expect(shouldAutoStartListening(stopped)).toBe(false)
  })

  it('10. a manual replay finishing naturally does not flag itself for automatic STT', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.SPEAK_REQUESTED, auto: false, attemptId: 1 }) // manual replay
    state = voiceReducer(state, { type: VOICE_ACTION.TTS_NATURAL_END, attemptId: 1 })

    expect(state.status).toBe(VOICE_STATUS.INTERVIEWER_FINISHED)
    expect(state.isAutomaticSpeech).toBe(false)
    expect(shouldAutoStartListening(state)).toBe(false)
  })

  it('11. disabling voice mode while TTS is speaking moves it out of INTERVIEWER_SPEAKING', () => {
    const speaking = voiceReducer(withVoiceMode(), { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })
    expect(speaking.status).toBe(VOICE_STATUS.INTERVIEWER_SPEAKING)

    const disabled = voiceReducer(speaking, { type: VOICE_ACTION.VOICE_MODE_DISABLED })

    expect(disabled.voiceMode).toBe(false)
    expect(disabled.status).toBe(VOICE_STATUS.TEXT_MODE)
    // A stray TTS_STOPPED for the old attempt must still be a safe no-op —
    // status already moved on.
    const afterStrayStop = voiceReducer(disabled, { type: VOICE_ACTION.TTS_STOPPED, attemptId: 1 })
    expect(afterStrayStop).toBe(disabled)
  })

  it('11b. disabling voice mode while the mic is recording leaves it alone (candidate controls when it stops)', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: false, attemptId: 1 })
    expect(state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)

    const disabled = voiceReducer(state, { type: VOICE_ACTION.VOICE_MODE_DISABLED })

    expect(disabled.voiceMode).toBe(false)
    expect(disabled.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING) // untouched, still recording
    expect(getActiveChannel(disabled)).toBe('mic')
  })

  it('12. a question change invalidates the previous question’s STT lifecycle too', () => {
    let state = withVoiceMode()
    state = voiceReducer(state, { type: VOICE_ACTION.LISTEN_REQUESTED, auto: true, attemptId: 1 })
    expect(state.status).toBe(VOICE_STATUS.CANDIDATE_LISTENING)

    state = voiceReducer(state, { type: VOICE_ACTION.QUESTION_CHANGED, questionId: 'q2', attemptId: 2 })
    expect(state.status).toBe(VOICE_STATUS.IDLE)

    const afterStaleFinal = voiceReducer(state, { type: VOICE_ACTION.STT_FINAL, attemptId: 1, transcript: 'stale answer' })

    expect(afterStaleFinal).toBe(state) // ignored — never overwrites the new question's blank transcript
    expect(afterStaleFinal.finalTranscript).toBe('')
  })

  it('13. a duplicated (StrictMode-like) lifecycle callback never produces a second logical transition', () => {
    const speaking = voiceReducer(withVoiceMode(), { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })

    const firstEnd = voiceReducer(speaking, { type: VOICE_ACTION.TTS_NATURAL_END, attemptId: 1 })
    expect(firstEnd.status).toBe(VOICE_STATUS.INTERVIEWER_FINISHED)

    // The exact same event fires again (e.g. a duplicated callback).
    const secondEnd = voiceReducer(firstEnd, { type: VOICE_ACTION.TTS_NATURAL_END, attemptId: 1 })

    expect(secondEnd).toBe(firstEnd) // no-op: status is no longer INTERVIEWER_SPEAKING
  })

  it('13b. a re-entrant SPEAK_REQUESTED while already speaking is a no-op, not a second attempt', () => {
    // The session hook never legitimately issues two overlapping
    // speak-requests, but the reducer's own guard (canStartSpeaking) is what
    // makes that true rather than convention: SPEAK_REQUESTED is only
    // honored from a rest/error state, so a duplicated request while
    // INTERVIEWER_SPEAKING can never silently swap out the attemptId a
    // real, in-flight utterance is still tied to.
    const speaking = voiceReducer(withVoiceMode(), { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 1 })

    const reentrant = voiceReducer(speaking, { type: VOICE_ACTION.SPEAK_REQUESTED, auto: true, attemptId: 2 })

    expect(reentrant).toBe(speaking)
    expect(reentrant.ttsAttemptId).toBe(1)
  })
})
