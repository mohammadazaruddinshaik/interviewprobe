import { useCallback, useEffect, useReducer, useRef } from 'react'
import { createVoiceProviders } from './providers/index.js'
import { createSpeechPresentation } from './speechPresentation.js'
import {
  createInitialVoiceState,
  getActiveChannel,
  getMicUiState,
  isSpeakerError,
  isSpeakerSpeaking,
  VOICE_STATUS,
} from './voiceState.js'
import { VOICE_ACTION, voiceReducer } from './voiceReducer.js'

// How long PROCESSING (candidate stopped talking, waiting for the
// provider's final transcript/close) is allowed to sit before this hook
// gives up waiting and recovers on its own. Deepgram normally follows
// UtteranceEnd with a final Results message (or a close) within a couple
// of seconds; this is a generous upper bound for the rare case where
// neither ever arrives, so the candidate is never left staring at a
// "Processing…" mic that can no longer be manually stopped (the mic
// control is disabled specifically while processing).
export const PROCESSING_TIMEOUT_MS = 8000

// Centralizes everything Interview.jsx used to track as separate flags
// (activeVoiceChannel, the auto-play/auto-listen refs) behind one reducer
// and one pair of provider adapters. Interview.jsx only needs to tell this
// hook which question is current and read back a small view model plus a
// handful of commands — it never owns any TTS/STT lifecycle detail itself.
//
// `onTranscript` is called with each finalized transcript exactly once
// (keyed by the STT attempt it came from, not by text equality, so a
// legitimately repeated phrase is never dropped) — this is how a final
// transcript reaches the candidate's answer text.
//
// `active` should be false once the interview leaves the 'ready' phase
// (completed, errored, still loading). Unlike the old per-question
// component remounting, this hook lives for the whole page's lifetime, so
// leaving 'ready' no longer implies an unmount that would otherwise stop
// any in-flight speech/listening on its own — this is what takes over that
// job instead.
export function useVoiceInterviewSession({ questionId, questionText, active = true, onTranscript }) {
  const [state, dispatch] = useReducer(voiceReducer, undefined, createInitialVoiceState)

  const onTranscriptRef = useRef(onTranscript)
  useEffect(() => {
    onTranscriptRef.current = onTranscript
  }, [onTranscript])

  const providersRef = useRef(null)
  if (!providersRef.current) providersRef.current = createVoiceProviders()
  const providers = providersRef.current

  // A plain, ever-increasing counter — not React state, since generating an
  // id must never itself trigger a render. Every attempt (a speak() call, a
  // start() call, a question reset) draws a fresh one; the reducer only
  // applies a lifecycle event whose attemptId matches the current one, which
  // is the single mechanism that makes stale/duplicate callbacks safe.
  const attemptCounterRef = useRef(0)
  const nextAttemptId = useCallback(() => {
    attemptCounterRef.current += 1
    return attemptCounterRef.current
  }, [])

  const speakQuestion = useCallback(
    (auto) => {
      if (!questionText) return
      const attemptId = nextAttemptId()
      dispatch({ type: VOICE_ACTION.SPEAK_REQUESTED, auto, attemptId })
      // The UI keeps showing questionText verbatim (rendered directly from
      // the question prop, never through this hook) — only what's handed
      // to the TTS provider goes through the deterministic speech
      // presentation layer first.
      const presentation = createSpeechPresentation(questionText)
      providers.tts.speak(presentation.text, {
        onStart: () => dispatch({ type: VOICE_ACTION.TTS_STARTED, attemptId }),
        onNaturalEnd: () => dispatch({ type: VOICE_ACTION.TTS_NATURAL_END, attemptId }),
        onStopped: () => dispatch({ type: VOICE_ACTION.TTS_STOPPED, attemptId }),
        onError: (error) => dispatch({ type: VOICE_ACTION.TTS_ERROR, attemptId, error }),
      })
    },
    [providers, questionText, nextAttemptId],
  )

  const startListening = useCallback(
    (auto) => {
      const attemptId = nextAttemptId()
      dispatch({ type: VOICE_ACTION.LISTEN_REQUESTED, auto, attemptId })
      providers.stt.start({
        onStart: () => dispatch({ type: VOICE_ACTION.STT_STARTED, attemptId }),
        onSpeechDetected: () => dispatch({ type: VOICE_ACTION.STT_SPEECH_DETECTED, attemptId }),
        onSpeechEnd: () => dispatch({ type: VOICE_ACTION.STT_SPEECH_ENDED, attemptId }),
        onInterim: (transcript) => dispatch({ type: VOICE_ACTION.STT_INTERIM, attemptId, transcript }),
        onFinal: (transcript) => dispatch({ type: VOICE_ACTION.STT_FINAL, attemptId, transcript }),
        onStopped: () => dispatch({ type: VOICE_ACTION.STT_STOPPED, attemptId }),
        onError: (error) => dispatch({ type: VOICE_ACTION.STT_ERROR, attemptId, error }),
      })
    },
    [providers, nextAttemptId],
  )

  // Public commands.
  const replayQuestion = useCallback(() => speakQuestion(false), [speakQuestion])
  const stopSpeaking = useCallback(() => providers.tts.stop(), [providers])
  const startListeningManually = useCallback(() => startListening(false), [startListening])
  const stopListening = useCallback(() => providers.stt.stop(), [providers])
  const clearError = useCallback(() => dispatch({ type: VOICE_ACTION.CLEAR_ERROR }), [])
  const resetForQuestion = useCallback(
    (newQuestionId) => {
      providers.tts.stop()
      providers.stt.stop()
      dispatch({ type: VOICE_ACTION.QUESTION_CHANGED, questionId: newQuestionId, attemptId: nextAttemptId() })
    },
    [providers, nextAttemptId],
  )

  // Question changes invalidate whatever the previous question's voice turn
  // was doing — this is what replaces the old key-remount-based reset.
  const previousQuestionIdRef = useRef(questionId)
  useEffect(() => {
    if (previousQuestionIdRef.current === questionId) return
    previousQuestionIdRef.current = questionId
    resetForQuestion(questionId)
    // resetForQuestion is stable (see its own deps) but intentionally left
    // out here: including it would re-run this effect whenever `providers`
    // is (re)read, which never happens after the first render anyway.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionId])

  // Speak the current question automatically, at most once per question.
  // Voice is the whole interview now, not a toggle, so this fires whenever
  // the session is active and at rest — no separate "voice mode" gate.
  const autoSpokenQuestionIdRef = useRef(null)
  useEffect(() => {
    if (!active) {
      autoSpokenQuestionIdRef.current = null
      return
    }
    if (!questionId || !questionText) return
    if (state.status !== VOICE_STATUS.IDLE) return
    if (autoSpokenQuestionIdRef.current === questionId) return
    autoSpokenQuestionIdRef.current = questionId
    speakQuestion(true)
  }, [active, state.status, questionId, questionText, speakQuestion])

  // The one place automatic listening is decided: only ever after automatic
  // playback's own natural end, never a manual replay's.
  useEffect(() => {
    if (state.status !== VOICE_STATUS.INTERVIEWER_FINISHED) return
    // Inlined rather than calling shouldAutoStartListening(state) here: an
    // exhaustive-deps lint can't see that helper only reads these two
    // fields, and would otherwise want the whole (fast-changing) state
    // object in this effect's deps.
    if (state.isAutomaticSpeech) {
      startListening(true)
    } else {
      dispatch({ type: VOICE_ACTION.SETTLE })
    }
  }, [state.status, state.isAutomaticSpeech, startListening])

  // Mirrors the latest state for the PROCESSING-timeout callback below,
  // which runs on a plain `setTimeout` outside React's render cycle and so
  // can't read `state` directly without risking a stale closure over
  // whatever it was when the effect that scheduled it last ran.
  const stateRef = useRef(state)
  useEffect(() => {
    stateRef.current = state
  }, [state])

  // Recovers from a stuck PROCESSING state: normally STT_SPEECH_ENDED
  // (Deepgram's UtteranceEnd) is followed shortly by either another
  // STT_FINAL (back to CANDIDATE_LISTENING) or STT_STOPPED/STT_ERROR (back
  // to rest) — see voiceReducer.js. If neither ever arrives, the mic
  // control is left disabled indefinitely (VoiceControls disables it while
  // processing) even though the candidate can still submit whatever was
  // already captured. This effect is keyed on `sttAttemptId`, exactly like
  // every other STT lifecycle event, so a question change or a fresh
  // listening attempt (both of which bump it) clears the previous timer
  // before this one can ever fire for the wrong attempt — the same
  // attempt-id race protection the rest of this hook already relies on.
  useEffect(() => {
    if (state.status !== VOICE_STATUS.PROCESSING) return
    const attemptId = state.sttAttemptId
    const timeoutId = setTimeout(() => {
      // Belt-and-suspenders on top of the effect's own dependency-driven
      // cleanup below: only recover if this is still the current attempt
      // and it's still stuck — never tear down a connection some newer,
      // legitimate attempt has since taken over.
      if (stateRef.current.sttAttemptId !== attemptId) return
      if (stateRef.current.status !== VOICE_STATUS.PROCESSING) return
      // stop() tears down the provider's connection and fires its own
      // onStopped callback (wired in startListening above), which
      // dispatches STT_STOPPED for this exact attemptId — the identical
      // path a manual stop takes. That reducer case returns to rest
      // without touching finalTranscript/finalTranscriptSeq, so whatever
      // was already captured is preserved, and nothing here ever submits
      // an answer.
      providers.stt.stop()
    }, PROCESSING_TIMEOUT_MS)
    return () => clearTimeout(timeoutId)
  }, [state.status, state.sttAttemptId, providers])

  // Delivers each finalized transcript chunk to the caller exactly once,
  // keyed by finalTranscriptSeq — a monotonic counter bumped on every
  // genuine STT_FINAL, unlike sttAttemptId (which stays constant across
  // multiple finals within one continuous-listening attempt, and so
  // couldn't signal "another chunk arrived" the way this does) or
  // sttAttemptId's own advance-per-attempt (which would otherwise re-deliver
  // stale text whenever a *later* attempt ended without producing a new
  // one). Each delivered chunk is a delta, not an accumulation — the
  // caller (Interview.jsx's handleVoiceTranscript) appends it to the
  // existing answer itself.
  const appliedTranscriptSeqRef = useRef(0)
  useEffect(() => {
    if (state.finalTranscriptSeq === 0) return
    if (appliedTranscriptSeqRef.current === state.finalTranscriptSeq) return
    appliedTranscriptSeqRef.current = state.finalTranscriptSeq
    onTranscriptRef.current?.(state.finalTranscript)
  }, [state.finalTranscript, state.finalTranscriptSeq])

  // Leaving the ready phase (completion, a load error, navigating away from
  // 'ready') stops any in-flight speech/listening immediately — the
  // equivalent of the unmount-based cleanup the old per-question-remounted
  // components got for free, now that this hook outlives any single phase.
  useEffect(() => {
    if (active) return
    providers.tts.stop()
    providers.stt.stop()
  }, [active, providers])

  useEffect(
    () => () => {
      providers.tts.dispose()
      providers.stt.dispose()
    },
    [providers],
  )

  return {
    state,
    activeChannel: getActiveChannel(state),
    isSpeakerSpeaking: isSpeakerSpeaking(state),
    isSpeakerError: isSpeakerError(state),
    micUiState: getMicUiState(state),
    ttsSupported: providers.tts.isSupported,
    sttSupported: providers.stt.isSupported,
    commands: {
      replayQuestion,
      stopSpeaking,
      startListening: startListeningManually,
      stopListening,
      resetForQuestion,
      clearError,
    },
  }
}
