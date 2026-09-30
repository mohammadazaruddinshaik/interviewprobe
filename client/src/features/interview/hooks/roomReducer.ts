import type { AnswerAttempt, InterviewState, Question, TranscriptEntry } from '../types/interview'

export type Turn =
  | { status: 'answering'; notice: string | null }
  | { status: 'submitting' }
  | { status: 'retryable'; message: string }
  | { status: 'rateLimited'; until: number; message: string }
  | { status: 'busy'; message: string }

export type EndFlow = { status: 'closed' | 'confirming' | 'ending' } | { status: 'error'; message: string }

export type RoomState =
  | { phase: 'loading' }
  | { phase: 'notFound' | 'unauthenticated' | 'loadError' | 'notStarted' | 'failed' }
  | {
      phase: 'ready'
      interview: InterviewState // server-derived
      question: Question // server-derived (lead_in only when it came from an answer response)
      draft: string // local
      attempt: AnswerAttempt | null // local, mirrored in sessionStorage
      turn: Turn // local
      transcript: TranscriptEntry[] // local, this browser session only
      endFlow: EndFlow // local
    }
  | { phase: 'completed' } // the room only redirects to the result page from here

export type RoomAction =
  | { type: 'LOADED'; interview: InterviewState; question: Question; attempt: AnswerAttempt | null }
  | { type: 'PHASE'; phase: 'notFound' | 'unauthenticated' | 'loadError' | 'notStarted' | 'failed' | 'loading' }
  | { type: 'DRAFT'; text: string }
  | { type: 'NOTICE'; message: string }
  | { type: 'SUBMIT_START'; attempt: AnswerAttempt }
  | { type: 'TURN'; turn: Turn }
  | { type: 'ACCEPTED'; question: Question; entry: TranscriptEntry }
  | { type: 'ENDED' }
  | { type: 'SYNC'; interview: InterviewState; notice?: string }
  | { type: 'DROP_ATTEMPT' }
  | { type: 'END_FLOW'; flow: EndFlow }

export function roomReducer(state: RoomState, action: RoomAction): RoomState {
  switch (action.type) {
    case 'LOADED': {
      const pending = action.attempt
      return {
        phase: 'ready',
        interview: action.interview,
        question: action.question,
        draft: pending ? pending.answer : '',
        attempt: pending,
        turn: pending
          ? { status: 'retryable', message: 'Your last answer may not have been received. Send it again to continue.' }
          : { status: 'answering', notice: null },
        transcript: [],
        endFlow: { status: 'closed' },
      }
    }
    case 'PHASE':
      return { phase: action.phase }
    case 'ENDED':
      return { phase: 'completed' }
    default:
      break
  }
  if (state.phase !== 'ready') return state

  switch (action.type) {
    case 'DRAFT':
      // Editing while an error is shown keeps the error (the next submit decides whether the key is reused).
      return { ...state, draft: action.text, turn: state.turn.status === 'answering' ? { status: 'answering', notice: null } : state.turn }
    case 'NOTICE':
      return { ...state, turn: { status: 'answering', notice: action.message } }
    case 'SUBMIT_START':
      return { ...state, attempt: action.attempt, turn: { status: 'submitting' } }
    case 'TURN':
      return { ...state, turn: action.turn }
    case 'ACCEPTED':
      return {
        ...state,
        question: action.question,
        draft: '',
        attempt: null,
        turn: { status: 'answering', notice: null },
        transcript: [...state.transcript, action.entry],
        interview: {
          ...state.interview,
          current_question_number: action.question.sequence,
          questions_answered: state.interview.questions_answered + 1,
          current_topic: action.question.topic,
        },
      }
    case 'SYNC': {
      const incoming = action.interview.current_question
      if (!incoming) return state
      const changed = incoming.id !== state.question.id
      return {
        ...state,
        interview: action.interview,
        question: changed ? incoming : state.question,
        draft: changed ? '' : state.draft,
        attempt: changed ? null : state.attempt,
        turn: changed ? { status: 'answering', notice: action.notice ?? null } : state.turn,
      }
    }
    case 'DROP_ATTEMPT':
      if (state.attempt === null) return state // e.g. a SYNC to a new question already cleared it
      return { ...state, attempt: null, turn: { status: 'answering', notice: 'We refreshed the interview. You can send your answer again.' } }
    case 'END_FLOW':
      return { ...state, endFlow: action.flow }
    default:
      return state
  }
}
