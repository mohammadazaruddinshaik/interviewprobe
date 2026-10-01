import { useCallback, useEffect, useRef } from 'react'
import { validateAnswer } from '../lib/idempotency'
import { useDictation, type DictationProblem } from '../voice/useDictation'
import { useSpeech } from '../voice/useSpeech'
import type { Question } from '../types/interview'
import type { Turn, EndFlow } from './roomReducer'

/** What the candidate sees. Derived from the room's lifecycle + the voice engines; never a second source of truth. */
export type Stage =
  | { kind: 'speechLoading' }
  | { kind: 'aiSpeaking' }
  | { kind: 'needsTap' } // the browser blocked autoplay until a tap
  | { kind: 'speechFailed'; message: string }
  | { kind: 'ready' } // question delivered; mic not open yet
  | { kind: 'connecting' }
  | { kind: 'listening' }
  | { kind: 'candidateSpeaking' }
  | { kind: 'finishing' } // collecting the final words
  | { kind: 'thinking' } // answer sent, waiting for the interviewer
  | { kind: 'completing' }
  | { kind: 'micProblem'; problem: DictationProblem }
  | { kind: 'retry'; message: string; restored: boolean; secondsLeft: number }

interface VoiceTurnInput {
  question: Question
  turn: Turn
  endFlow: EndFlow
  attemptAnswer: string | null
  secondsLeft: number
  submit: (spoken: string) => Promise<void>
  discardAttempt: () => void
  notify: (message: string) => void
}

const spokenText = (q: Question) => `${q.lead_in ? `${q.lead_in} ` : ''}${q.text}`.slice(0, 2000)

export function useVoiceTurn({ question, turn, endFlow, attemptAnswer, secondsLeft, submit, discardAttempt, notify }: VoiceTurnInput) {
  const speech = useSpeech()
  const dictation = useDictation()
  const { speak, stop: stopSpeech } = speech
  const { start: startMic, cancel: cancelMic, finish: finishMic } = dictation
  const questionRef = useRef(question)
  useEffect(() => {
    questionRef.current = question
  })

  // A new question (first load, or the backend's next question) is spoken. A restored, unsent answer is not.
  const hadAttempt = useRef(attemptAnswer !== null)
  useEffect(() => {
    cancelMic()
    if (hadAttempt.current) {
      hadAttempt.current = false
      return
    }
    void speak(spokenText(question))
  }, [question.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // When the interviewer finishes speaking, open the microphone. Nothing is ever submitted automatically.
  const speechStatus = speech.state.status
  const answering = turn.status === 'answering'
  const canListenRef = useRef(false)
  useEffect(() => {
    canListenRef.current = answering && endFlow.status === 'closed'
  })
  const finishedUtterances = speech.finished
  useEffect(() => {
    // Keyed to the utterance-finished EVENT so a stale "ended" status can never reopen the mic mid-question.
    if (finishedUtterances > 0 && canListenRef.current) void startMic()
  }, [finishedUtterances, startMic])

  // Ending the interview releases every media resource first.
  const ending = endFlow.status === 'ending'
  useEffect(() => {
    if (!ending) return
    stopSpeech()
    cancelMic()
  }, [ending, stopSpeech, cancelMic])

  const finishAnswer = useCallback(async () => {
    const text = await finishMic()
    const checked = validateAnswer(text)
    if (!checked.ok) {
      notify(checked.message)
      void startMic() // keep the conversation going: the mic reopens for another try
      return
    }
    await submit(checked.answer)
  }, [finishMic, notify, startMic, submit])

  const replay = useCallback(() => {
    cancelMic()
    void speak(spokenText(questionRef.current))
  }, [cancelMic, speak])

  const retrySend = useCallback(() => {
    if (attemptAnswer) void submit(attemptAnswer)
  }, [attemptAnswer, submit])

  const answerAgain = useCallback(() => {
    discardAttempt()
    void startMic()
  }, [discardAttempt, startMic])

  const speakNow = useCallback(() => void speak(spokenText(questionRef.current)), [speak])

  // ---- stage derivation (order = priority) ----
  const mic = dictation.state
  const heard = (dictation.finalText + dictation.interim).trim().length > 0
  let stage: Stage
  if (ending) stage = { kind: 'completing' }
  else if (turn.status === 'submitting') stage = { kind: 'thinking' }
  else if (mic.status === 'finishing') stage = { kind: 'finishing' }
  else if (turn.status === 'retryable' || turn.status === 'rateLimited' || turn.status === 'busy') {
    stage = { kind: 'retry', message: turn.message, restored: turn.status === 'retryable' && attemptAnswer !== null, secondsLeft }
  } else if (speechStatus === 'loading') stage = { kind: 'speechLoading' }
  else if (speechStatus === 'playing') stage = { kind: 'aiSpeaking' }
  else if (speechStatus === 'blocked') stage = { kind: 'needsTap' }
  else if (speechStatus === 'error' && mic.status === 'idle') stage = { kind: 'speechFailed', message: speech.state.status === 'error' ? speech.state.message : '' }
  else if (mic.status === 'error') stage = { kind: 'micProblem', problem: mic.problem }
  else if (mic.status === 'connecting') stage = { kind: 'connecting' }
  else if (mic.status === 'live') stage = heard ? { kind: 'candidateSpeaking' } : { kind: 'listening' }
  else stage = { kind: 'ready' }

  return {
    stage,
    notice: turn.status === 'answering' ? turn.notice : null,
    transcript: { final: dictation.finalText, interim: dictation.interim },
    speechMeter: () => speech.meter.current,
    micMeter: () => dictation.meter.current,
    actions: { finishAnswer, replay, retrySend, answerAgain, speakNow, startMic, cancelMic },
  }
}
