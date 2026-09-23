import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { getInterview, startInterview, submitInterviewAnswer } from '../api/interviews.js'
import InterviewComplete from '../components/interview/InterviewComplete.jsx'
import InterviewError from '../components/interview/InterviewError.jsx'
import InterviewLoading from '../components/interview/InterviewLoading.jsx'
import VoiceInterviewView from '../components/interview/voice/VoiceInterviewView.jsx'
import { DIFFICULTY_LABELS, ROLE_LABELS, TOPIC_LABELS } from '../data/interviewCatalog.js'
import { useVoiceInterviewSession } from '../voice/useVoiceInterviewSession.js'

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

  async function handleSubmit() {
    const trimmedAnswer = answer.trim()
    if (!trimmedAnswer || isSubmitting || !question) return

    if (idempotencyRef.current.key === null || idempotencyRef.current.answer !== trimmedAnswer) {
      idempotencyRef.current = { key: crypto.randomUUID(), answer: trimmedAnswer }
    }

    setIsSubmitting(true)
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
  // `question`/`answer`/`handleSubmit`/`voice` state this page has always
  // owned; only the rendering is voice-first now.
  return (
    <div className="min-h-screen bg-cream">
      <VoiceInterviewView
        voice={voice}
        question={question}
        questionLimit={sessionMeta?.questionLimit}
        roleLabel={ROLE_LABELS[sessionMeta?.role] ?? sessionMeta?.role}
        difficultyLabel={DIFFICULTY_LABELS[sessionMeta?.difficulty] ?? sessionMeta?.difficulty}
        topicLabel={TOPIC_LABELS[question?.topic] ?? question?.topic}
        answer={answer}
        onAnswerChange={setAnswer}
        onSubmit={handleSubmit}
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
