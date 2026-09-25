import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { getInterview, startInterview, submitInterviewAnswer } from '../api/interviews.js'
import InterviewComplete from '../components/interview/InterviewComplete.jsx'
import InterviewError from '../components/interview/InterviewError.jsx'
import InterviewLoading from '../components/interview/InterviewLoading.jsx'
import VoiceInterviewView from '../components/interview/voice/VoiceInterviewView.jsx'
import { ROLE_LABELS } from '../data/interviewCatalog.js'
import { useVoiceInterviewSession } from '../voice/useVoiceInterviewSession.js'
import { VOICE_STATUS } from '../voice/voiceState.js'

const GENERIC_LOAD_ERROR = 'Something went wrong while loading your interview.'
const GENERIC_SUBMIT_ERROR = 'Something went wrong while submitting your answer.'

function Interview() {
  const { sessionId } = useParams()

  // 'loading' | 'error' | 'restore_failed' | 'ready' | 'completed'
  const [phase, setPhase] = useState('loading')
  const [loadError, setLoadError] = useState(null)
  const [sessionMeta, setSessionMeta] = useState(null)
  const [question, setQuestion] = useState(null)
  const [answer, setAnswer] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  // null | 'stt' | 'ready' — set the moment Finish Answer is clicked with
  // the mic still active, tracking the two-stage wait described on the
  // effect below: 'stt' until voice.commands.finishListening() has left
  // PROCESSING, then one extra render as 'ready' before actually
  // submitting. Distinct from isSubmitting, which covers the whole
  // finish-then-submit window (both this wait and the actual API call) for
  // the button's busy state.
  const [awaitingFinish, setAwaitingFinish] = useState(null)

  // Tracks the idempotency key for the *current* answer attempt: reused
  // across retries of the same unsubmitted answer text, replaced with a
  // fresh one if the candidate edits the answer (the backend fingerprints
  // {question_id, answer} against the key, so reusing it with different
  // text would be rejected as a reused-key conflict).
  const idempotencyRef = useRef({ key: null, answer: null })
  const questionHeadingRef = useRef(null)

  // Voice only ever appends recognized text into the same value typing
  // produces — it never submits the answer itself, so the result behaves
  // exactly like manually typed text from this point on. Wrapped in
  // useCallback so the session hook's internal delivery effect (which reads
  // it via a ref) never sees a "changed" callback on every render.
  const handleVoiceTranscript = useCallback((transcript) => {
    setAnswer((current) => (current.trim() ? `${current.trim()} ${transcript}` : transcript))
  }, [])

  // Owns every TTS/STT lifecycle detail (auto-play, auto-listen, the
  // speaker/mic mutual lock, question-change cleanup, StrictMode-safety)
  // behind one small view model + a handful of commands — Interview.jsx no
  // longer tracks any of that itself.
  const voice = useVoiceInterviewSession({
    questionId: question?.id,
    questionText: question?.text,
    questionLeadIn: question?.lead_in,
    active: phase === 'ready',
    onTranscript: handleVoiceTranscript,
  })

  useEffect(() => {
    let cancelled = false

    async function load() {
      setPhase('loading')
      setLoadError(null)
      try {
        const interview = await getInterview(sessionId)
        if (cancelled) return

        setSessionMeta({
          role: interview.role,
          difficulty: interview.difficulty,
          questionLimit: interview.question_limit,
        })

        if (interview.status === 'COMPLETED') {
          setPhase('completed')
          return
        }

        if (interview.status === 'CREATED') {
          const started = await startInterview(sessionId)
          if (cancelled) return
          setQuestion(started.question)
          setPhase('ready')
          return
        }

        if (interview.status === 'IN_PROGRESS') {
          // `GET /interviews/{id}` now returns the current unanswered
          // question directly (Task 27) — a refresh restores it instead of
          // calling `start` again, which the backend would reject (409):
          // it only accepts CREATED sessions.
          if (interview.current_question) {
            setQuestion(interview.current_question)
            setPhase('ready')
            return
          }
          // Data-integrity fallback only — should not happen in practice.
          // Never guess a question or call the LLM just to paper over it.
          setPhase('restore_failed')
          return
        }

        setPhase('error')
        setLoadError('This interview cannot be continued.')
      } catch (error) {
        if (cancelled) return
        setLoadError(error instanceof ApiError ? error.message : GENERIC_LOAD_ERROR)
        setPhase('error')
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [sessionId, retryCount])

  useEffect(() => {
    if (phase === 'ready' && question) {
      questionHeadingRef.current?.focus()
    }
  }, [phase, question])

  // The one and only place that actually calls the submit API — reached
  // either directly (mic wasn't active) or after finishListening() has
  // settled (mic was active). isSubmitting is already true by the time this
  // runs either way, so it is deliberately NOT part of this function's own
  // guard — see handleFinishAnswer, the single gatekeeper for starting a
  // finish/submit cycle at all.
  async function submitAnswer() {
    const trimmedAnswer = answer.trim()
    if (!trimmedAnswer || !question) {
      // Nothing meaningful was captured (e.g. the candidate finished
      // listening without ever having spoken/typed anything) — never
      // submit an empty or stale answer.
      setIsSubmitting(false)
      return
    }

    if (idempotencyRef.current.key === null || idempotencyRef.current.answer !== trimmedAnswer) {
      idempotencyRef.current = { key: crypto.randomUUID(), answer: trimmedAnswer }
    }

    setSubmitError(null)
    try {
      const result = await submitInterviewAnswer(sessionId, {
        questionId: question.id,
        answer: trimmedAnswer,
        idempotencyKey: idempotencyRef.current.key,
      })

      idempotencyRef.current = { key: null, answer: null }
      setAnswer('')

      if (result.question) {
        setQuestion(result.question)
        setIsSubmitting(false)
      } else {
        setPhase('completed')
      }
    } catch (error) {
      // The typed answer (`answer` state) is deliberately left untouched
      // here so a failed submission never loses the candidate's work.
      setSubmitError(error instanceof ApiError ? error.message : GENERIC_SUBMIT_ERROR)
      setIsSubmitting(false)
    }
  }

  // The candidate's explicit "I'm done" — the only entry point into a
  // finish/submit cycle (never a pause, never a Deepgram UtteranceEnd; see
  // voiceReducer.js's FINISH_REQUESTED). If the mic is currently listening,
  // it must be cleanly wound down first — including a trailing final
  // transcript for whatever was just said — before submitAnswer() reads
  // `answer`, so a final transcript that was still finalizing at the exact
  // moment of the click is never lost or raced. If the mic isn't active
  // (typed answer, or already stopped), there's nothing to wait for and
  // this proceeds straight to submitting, exactly as before.
  function handleFinishAnswer() {
    if (isSubmitting || !answer.trim() || !question) return
    setIsSubmitting(true)
    setSubmitError(null)

    const micActive =
      voice.state.status === VOICE_STATUS.CANDIDATE_LISTENING || voice.state.status === VOICE_STATUS.CANDIDATE_SPEAKING
    if (!micActive) {
      submitAnswer()
      return
    }
    setAwaitingFinish('stt')
    voice.commands.finishListening()
  }

  // Two stages, not one, deliberately: a trailing final transcript's own
  // delivery (useVoiceInterviewSession's delivery effect -> setAnswer) can
  // land in the very same React commit as the PROCESSING -> IDLE transition
  // this effect watches for (e.g. a provider whose stop() resolves
  // "instantly enough" that Deepgram's trailing final and its onStopped
  // both fire within one batch). If that happens, `answer` in THIS
  // render's closure is still the pre-delivery value — setAnswer only
  // schedules a future render, it doesn't retroactively update a closure
  // already captured this render. Moving to 'ready' (rather than
  // submitting immediately) forces one more render to happen first; by the
  // time that one runs, any same-commit setAnswer has already been applied,
  // so 'ready''s branch is guaranteed to see the fully-settled answer.
  useEffect(() => {
    if (awaitingFinish === 'stt') {
      if (voice.state.status === VOICE_STATUS.PROCESSING) return
      setAwaitingFinish('ready')
      return
    }
    if (awaitingFinish === 'ready') {
      setAwaitingFinish(null)
      submitAnswer()
    }
    // submitAnswer/answer/question/sessionId intentionally omitted: this
    // effect must fire exactly once per finish request, driven solely by
    // awaitingFinish/voice.state.status, and always reads the latest
    // `answer` via the closure created on the render where 'ready' fires.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [awaitingFinish, voice.state.status])

  function handleRetryLoad() {
    setRetryCount((count) => count + 1)
  }

  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-cream">
        <InterviewLoading />
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="min-h-screen bg-cream">
        <InterviewError message={loadError ?? GENERIC_LOAD_ERROR} onRetry={handleRetryLoad} />
      </div>
    )
  }

  if (phase === 'restore_failed') {
    return (
      <div className="min-h-screen bg-cream">
        <InterviewError message="Interview state couldn't be restored. Please try again." onRetry={handleRetryLoad}>
          <Link to="/interview/new" className="mt-4 inline-block text-sm font-medium text-accent hover:underline">
            Start a new interview
          </Link>
        </InterviewError>
      </div>
    )
  }

  if (phase === 'completed') {
    return (
      <div className="min-h-screen bg-cream">
        <InterviewComplete sessionId={sessionId} />
      </div>
    )
  }

  // Voice is the interview — the room is the only interview workspace, not
  // one of two presentations. It reads the exact same
  // `question`/`answer`/`handleFinishAnswer`/`voice` state this page has
  // always owned; only the rendering is voice-first now.
  return (
    <div className="min-h-screen bg-cream">
      <VoiceInterviewView
        voice={voice}
        question={question}
        roleLabel={ROLE_LABELS[sessionMeta?.role] ?? sessionMeta?.role}
        answer={answer}
        onAnswerChange={setAnswer}
        onSubmit={handleFinishAnswer}
        submitting={isSubmitting}
        headingRef={questionHeadingRef}
      />

      {submitError && (
        <div className="mx-auto max-w-3xl px-6 pb-12 sm:px-8">
          <p role="alert" aria-live="assertive" className="text-center text-sm text-error">
            {submitError}
          </p>
        </div>
      )}
    </div>
  )
}

export default Interview
