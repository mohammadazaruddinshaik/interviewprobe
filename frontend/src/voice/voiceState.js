// The voice session's logical states. A candidate can never be simultaneously
// "the interviewer is speaking" and "the candidate is speaking" because these
// are branches of one enum, not independent booleans — impossible states are
// structurally unrepresentable rather than merely guarded against.
//
// Voice is the interview — there is no separate "text mode" to fall back to
// or toggle away from, so IDLE (nothing speaking/listening yet) is the only
// rest state.
export const VOICE_STATUS = {
  IDLE: 'IDLE',
  INTERVIEWER_SPEAKING: 'INTERVIEWER_SPEAKING',
  INTERVIEWER_FINISHED: 'INTERVIEWER_FINISHED', // transient: TTS just ended naturally
  CANDIDATE_LISTENING: 'CANDIDATE_LISTENING', // mic open, no speech detected yet
  CANDIDATE_SPEAKING: 'CANDIDATE_SPEAKING', // mic open, speech detected
  PROCESSING: 'PROCESSING', // candidate stopped talking, finalizing the transcript
  ERROR: 'ERROR',
}

const MIC_BUSY_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

export function createInitialVoiceState() {
  return {
    status: VOICE_STATUS.IDLE,
    questionId: null,
    // Whether the in-flight/last TTS attempt was the automatic (question-
    // triggered) one, as opposed to a manual replay — this is what decides
    // whether a natural completion is allowed to auto-start the mic.
    isAutomaticSpeech: false,
    // Monotonically increasing ids, assigned by the caller (the session
    // hook) whenever a new attempt starts. Every lifecycle event carries the
    // attemptId it belongs to; the reducer only applies an event if it
    // matches the *current* attempt, so a stale callback from a superseded
    // utterance/recognition session (a cancelled question, a StrictMode
    // double-invoke, a race) can never mutate state it no longer owns.
    ttsAttemptId: 0,
    sttAttemptId: 0,
    interimTranscript: '',
    // Holds only the most recent finalized chunk, not an accumulation — a
    // provider (Deepgram) may deliver several of these across one listening
    // attempt as the candidate speaks in segments; each is appended to the
    // answer by the consumer (see useVoiceInterviewSession's delivery
    // effect), not by this reducer.
    finalTranscript: '',
    // Incremented on every genuine STT_FINAL, never on STT_STOPPED/STT_ERROR
    // — a monotonic "a new chunk was delivered" marker a consumer can watch
    // for change. Deliberately a sequence, not the attemptId: attemptId
    // stays constant across multiple finals within one attempt, so it can't
    // signal "another chunk arrived" the way this can.
    finalTranscriptSeq: 0,
    // { code, message, recoverable, source: 'tts' | 'stt' } | null
    error: null,
  }
}

// Which voice channel currently holds the microphone/speaker lock — derived
// from `status`, never stored redundantly, so it can never disagree with it.
export function getActiveChannel(state) {
  if (state.status === VOICE_STATUS.INTERVIEWER_SPEAKING) return 'speaker'
  if (MIC_BUSY_STATUSES.includes(state.status)) return 'mic'
  return null
}

// True only in the narrow window this task cares about: automatic playback
// (never a manual replay) just finished on its own (never a cancellation).
export function shouldAutoStartListening(state) {
  return state.status === VOICE_STATUS.INTERVIEWER_FINISHED && state.isAutomaticSpeech === true
}

// Maps the full state machine onto the small set of visual mic states the
// room's controls render (idle/listening/processing/error) —
// CANDIDATE_LISTENING and CANDIDATE_SPEAKING both read as "listening".
export function getMicUiState(state) {
  if (state.status === VOICE_STATUS.CANDIDATE_LISTENING || state.status === VOICE_STATUS.CANDIDATE_SPEAKING) {
    return 'listening'
  }
  if (state.status === VOICE_STATUS.PROCESSING) return 'processing'
  if (state.status === VOICE_STATUS.ERROR && state.error?.source === 'stt') return 'error'
  return 'idle'
}

export function isSpeakerSpeaking(state) {
  return state.status === VOICE_STATUS.INTERVIEWER_SPEAKING
}

export function isSpeakerError(state) {
  return state.status === VOICE_STATUS.ERROR && state.error?.source === 'tts'
}

const START_SPEAKING_ALLOWED = [VOICE_STATUS.IDLE, VOICE_STATUS.ERROR]
const START_LISTENING_ALLOWED = [VOICE_STATUS.IDLE, VOICE_STATUS.ERROR, VOICE_STATUS.INTERVIEWER_FINISHED]

export function canStartSpeaking(state) {
  return START_SPEAKING_ALLOWED.includes(state.status)
}

export function canStartListening(state) {
  return START_LISTENING_ALLOWED.includes(state.status)
}
