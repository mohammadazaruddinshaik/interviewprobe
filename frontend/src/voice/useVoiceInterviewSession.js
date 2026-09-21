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

// Centralizes everything Interview.jsx used to track as separate flags
// (activeVoiceChannel, voiceMode, the auto-play/auto-listen refs) behind one
// reducer and one pair of provider adapters. Interview.jsx now only needs to
// tell this hook which question is current and read back a small view model
// plus a handful of commands — it no longer owns any TTS/STT lifecycle
// detail itself.
//
// `onTranscript` is called with each finalized transcript exactly once
// (keyed by the STT attempt it came from, not by text equality, so a
// legitimately repeated phrase is never dropped) — this is how a final
// transcript reaches AnswerEditor's answer text, mirroring what
// VoiceInputButton's onTranscript callback did before this task.
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
      // The UI keeps showing questionText verbatim (QuestionPanel reads
      // question.text directly, never through this hook) — only what's
      // handed to the TTS provider goes through the deterministic speech
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
  const enableVoiceMode = useCallback(() => dispatch({ type: VOICE_ACTION.VOICE_MODE_ENABLED }), [])
  const disableVoiceMode = useCallback(() => {
    // TTS is always interrupted by a mode change; the reducer decides
    // whether a busy mic is left alone (it is, deliberately).
    providers.tts.stop()
    dispatch({ type: VOICE_ACTION.VOICE_MODE_DISABLED })
  }, [providers])
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

  // Speak the current question automatically, at most once per question,
  // whenever voice mode is (or becomes) on. Reset when voice mode turns off
  // so re-enabling it speaks the current question fresh rather than staying
  // silent because "we already spoke this one" — see QuestionSpeaker's
  // Task 35/36 history for why this must not fire twice on a fresh mount
  // whose voiceMode starts already true: that scenario never happens here,
  // since voiceMode always starts false and only flips true from a later,
  // user-triggered render, well outside any mount-time double-invocation.
  const autoSpokenQuestionIdRef = useRef(null)
  useEffect(() => {
    if (!state.voiceMode) {
      autoSpokenQuestionIdRef.current = null
      return
    }
    if (!questionId || !questionText) return
    if (state.status !== VOICE_STATUS.IDLE) return
    if (autoSpokenQuestionIdRef.current === questionId) return
    autoSpokenQuestionIdRef.current = questionId
    speakQuestion(true)
  }, [state.voiceMode, state.status, questionId, questionText, speakQuestion])

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
      enableVoiceMode,
      disableVoiceMode,
      replayQuestion,
      stopSpeaking,
      startListening: startListeningManually,
      stopListening,
      resetForQuestion,
      clearError,
    },
  }
}
