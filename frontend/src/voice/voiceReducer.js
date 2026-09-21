import { canStartListening, canStartSpeaking, VOICE_STATUS } from './voiceState.js'

export const VOICE_ACTION = {
  VOICE_MODE_ENABLED: 'VOICE_MODE_ENABLED',
  VOICE_MODE_DISABLED: 'VOICE_MODE_DISABLED',
  QUESTION_CHANGED: 'QUESTION_CHANGED',
  SPEAK_REQUESTED: 'SPEAK_REQUESTED',
  TTS_STARTED: 'TTS_STARTED',
  TTS_NATURAL_END: 'TTS_NATURAL_END',
  TTS_STOPPED: 'TTS_STOPPED',
  TTS_ERROR: 'TTS_ERROR',
  LISTEN_REQUESTED: 'LISTEN_REQUESTED',
  STT_STARTED: 'STT_STARTED',
  STT_SPEECH_DETECTED: 'STT_SPEECH_DETECTED',
  STT_SPEECH_ENDED: 'STT_SPEECH_ENDED',
  STT_INTERIM: 'STT_INTERIM',
  STT_FINAL: 'STT_FINAL',
  STT_STOPPED: 'STT_STOPPED',
  STT_ERROR: 'STT_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SETTLE: 'SETTLE',
}

const MIC_BUSY = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

function restStatus(state) {
  return state.voiceMode ? VOICE_STATUS.IDLE : VOICE_STATUS.TEXT_MODE
}

// Every lifecycle action (TTS_*, STT_*) carries the attemptId it belongs to.
// Comparing it against the reducer's own counter is what makes a stale event
// from a superseded attempt a guaranteed no-op, regardless of what caused
// the staleness (a question change, a cancellation, a duplicate callback).
function isCurrentTtsAttempt(state, action) {
  return action.attemptId === state.ttsAttemptId
}
function isCurrentSttAttempt(state, action) {
  return action.attemptId === state.sttAttemptId
}

export function voiceReducer(state, action) {
  switch (action.type) {
    case VOICE_ACTION.VOICE_MODE_ENABLED: {
      if (state.voiceMode) return state
      return { ...state, voiceMode: true, status: VOICE_STATUS.IDLE, error: null }
    }

    case VOICE_ACTION.VOICE_MODE_DISABLED: {
      if (!state.voiceMode) return state
      // A microphone already recording is left alone — the candidate, not a
      // mode toggle, controls when their own capture stops (unchanged from
      // the existing behavior this replaces).
      const micBusy = MIC_BUSY.includes(state.status)
      return {
        ...state,
        voiceMode: false,
        status: micBusy ? state.status : VOICE_STATUS.TEXT_MODE,
        error: micBusy ? state.error : null,
      }
    }

    case VOICE_ACTION.QUESTION_CHANGED: {
      // Bumping both attempt ids orphans any callback still in flight for
      // the previous question, even if nothing new has started yet.
      return {
        ...state,
        questionId: action.questionId,
        status: restStatus(state),
        isAutomaticSpeech: false,
        interimTranscript: '',
        finalTranscript: '',
        finalTranscriptSeq: 0,
        error: null,
        ttsAttemptId: action.attemptId,
        sttAttemptId: action.attemptId,
      }
    }

    case VOICE_ACTION.SPEAK_REQUESTED: {
      if (!canStartSpeaking(state)) return state
      return {
        ...state,
        status: VOICE_STATUS.INTERVIEWER_SPEAKING,
        isAutomaticSpeech: Boolean(action.auto),
        ttsAttemptId: action.attemptId,
        error: null,
      }
    }

    case VOICE_ACTION.TTS_STARTED: {
      // Informational only — status is already INTERVIEWER_SPEAKING from
      // SPEAK_REQUESTED. Kept as a distinct action for symmetry with STT and
      // so a future provider can signal "actually started" separately from
      // "was asked to start" without a reducer change.
      return state
    }

    case VOICE_ACTION.TTS_NATURAL_END: {
      if (!isCurrentTtsAttempt(state, action) || state.status !== VOICE_STATUS.INTERVIEWER_SPEAKING) return state
      return { ...state, status: VOICE_STATUS.INTERVIEWER_FINISHED }
    }

    case VOICE_ACTION.TTS_STOPPED: {
      if (!isCurrentTtsAttempt(state, action) || state.status !== VOICE_STATUS.INTERVIEWER_SPEAKING) return state
      // Deliberately returns to rest, never to INTERVIEWER_FINISHED — a
      // cancellation must never be interpreted as a natural completion.
      return { ...state, status: restStatus(state) }
    }

    case VOICE_ACTION.TTS_ERROR: {
      if (!isCurrentTtsAttempt(state, action)) return state
      return { ...state, status: VOICE_STATUS.ERROR, error: { ...action.error, source: 'tts' } }
    }

    case VOICE_ACTION.LISTEN_REQUESTED: {
      if (!canStartListening(state)) return state
      return {
        ...state,
        status: VOICE_STATUS.CANDIDATE_LISTENING,
        sttAttemptId: action.attemptId,
        interimTranscript: '',
        error: null,
      }
    }

    case VOICE_ACTION.STT_STARTED: {
      return state // informational only, same reasoning as TTS_STARTED
    }

    case VOICE_ACTION.STT_SPEECH_DETECTED: {
      if (!isCurrentSttAttempt(state, action) || state.status !== VOICE_STATUS.CANDIDATE_LISTENING) return state
      return { ...state, status: VOICE_STATUS.CANDIDATE_SPEAKING }
    }

    case VOICE_ACTION.STT_INTERIM: {
      if (!isCurrentSttAttempt(state, action)) return state
      if (state.status !== VOICE_STATUS.CANDIDATE_LISTENING && state.status !== VOICE_STATUS.CANDIDATE_SPEAKING) {
        return state
      }
      return { ...state, status: VOICE_STATUS.CANDIDATE_SPEAKING, interimTranscript: action.transcript }
    }

    case VOICE_ACTION.STT_SPEECH_ENDED: {
      if (!isCurrentSttAttempt(state, action)) return state
      if (state.status !== VOICE_STATUS.CANDIDATE_LISTENING && state.status !== VOICE_STATUS.CANDIDATE_SPEAKING) {
        return state
      }
      return { ...state, status: VOICE_STATUS.PROCESSING }
    }

    case VOICE_ACTION.STT_FINAL: {
      if (!isCurrentSttAttempt(state, action)) return state
      if (!MIC_BUSY.includes(state.status)) return state
      // Deliberately stays in CANDIDATE_LISTENING rather than resting: a
      // provider that supports continuous listening (Deepgram) may still be
      // capturing more speech after this chunk. The attempt only truly ends
      // via STT_STOPPED/STT_ERROR — every provider, including the
      // single-shot browser one, is responsible for eventually producing
      // one of those once it's done, whether or not a final preceded it.
      return {
        ...state,
        status: VOICE_STATUS.CANDIDATE_LISTENING,
        finalTranscript: action.transcript,
        finalTranscriptSeq: state.finalTranscriptSeq + 1,
        interimTranscript: '',
      }
    }

    case VOICE_ACTION.STT_STOPPED: {
      if (!isCurrentSttAttempt(state, action)) return state
      if (!MIC_BUSY.includes(state.status)) return state
      return { ...state, status: restStatus(state), interimTranscript: '' }
    }

    case VOICE_ACTION.STT_ERROR: {
      if (!isCurrentSttAttempt(state, action)) return state
      return { ...state, status: VOICE_STATUS.ERROR, error: { ...action.error, source: 'stt' }, interimTranscript: '' }
    }

    case VOICE_ACTION.CLEAR_ERROR: {
      if (state.status !== VOICE_STATUS.ERROR) return state
      return { ...state, status: restStatus(state), error: null }
    }

    // Dispatched by the session hook when INTERVIEWER_FINISHED was reached
    // by a *manual* replay (isAutomaticSpeech false) — nothing should
    // auto-start, so this just returns to rest instead of lingering in a
    // transient state forever.
    case VOICE_ACTION.SETTLE: {
      if (state.status !== VOICE_STATUS.INTERVIEWER_FINISHED) return state
      return { ...state, status: restStatus(state) }
    }

    default:
      return state
  }
}
