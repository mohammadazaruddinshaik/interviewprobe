import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { getInterviewResult } from '../api/interviews.js'
import EvidenceSection from '../components/result/EvidenceSection.jsx'
import FeedbackList from '../components/result/FeedbackList.jsx'
import QuestionReview from '../components/result/QuestionReview.jsx'
import ResultHeader from '../components/result/ResultHeader.jsx'
import ResultLoading from '../components/result/ResultLoading.jsx'
import ScoreDimensions from '../components/result/ScoreDimensions.jsx'
import ScoreHero from '../components/result/ScoreHero.jsx'
import InterviewError from '../components/interview/InterviewError.jsx'
import Button from '../components/ui/Button.jsx'
import { CheckIcon, TargetIcon } from '../components/ui/icons.jsx'
import { DIFFICULTY_LABELS, ROLE_LABELS } from '../data/interviewCatalog.js'

const GENERIC_LOAD_ERROR = 'Something went wrong while loading your results.'
const INCOMPLETE_MESSAGE = 'Complete your interview before viewing results.'

function InterviewResult() {
  const { sessionId } = useParams()

  // 'loading' | 'error' | 'incomplete' | 'ready'
  const [phase, setPhase] = useState('loading')
  const [loadError, setLoadError] = useState(null)
  const [result, setResult] = useState(null)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setPhase('loading')
      setLoadError(null)
      try {
        // A single call — the backend lazily creates the evaluation here
        // if needed, so the frontend never calls a separate evaluation
        // endpoint or duplicates that request.
        const data = await getInterviewResult(sessionId)
        if (cancelled) return
        setResult(data)
        setPhase('ready')
      } catch (error) {
        if (cancelled) return
        if (error instanceof ApiError && error.code === 'INVALID_INTERVIEW_STATE') {
          setPhase('incomplete')
          return
        }
        setLoadError(error instanceof ApiError ? error.message : GENERIC_LOAD_ERROR)
        setPhase('error')
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [sessionId, retryCount])

  function handleRetry() {
    setRetryCount((count) => count + 1)
  }

  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-cream">
        <ResultLoading />
      </div>
    )
  }

  if (phase === 'incomplete') {
    return (
      <div className="min-h-screen bg-cream">
        <InterviewError message={INCOMPLETE_MESSAGE}>
          <Link
            to={`/interview/${sessionId}`}
            className="mt-4 inline-block text-sm font-medium text-accent hover:underline"
          >
            Continue interview
          </Link>
        </InterviewError>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="min-h-screen bg-cream">
        <InterviewError message={loadError ?? GENERIC_LOAD_ERROR} onRetry={handleRetry}>
          <Link to="/" className="mt-4 inline-block text-sm font-medium text-accent hover:underline">
            Back to home
          </Link>
        </InterviewError>
      </div>
    )
  }

  const { interview, questions, evaluation } = result

  return (
    <div className="min-h-screen bg-cream">
      <ResultHeader
        roleLabel={ROLE_LABELS[interview.role] ?? interview.role}
        difficultyLabel={DIFFICULTY_LABELS[interview.difficulty] ?? interview.difficulty}
      />

      <main>
        <ScoreHero
          overallScore={evaluation.overall_score}
          roleLabel={ROLE_LABELS[interview.role] ?? interview.role}
          difficultyLabel={DIFFICULTY_LABELS[interview.difficulty] ?? interview.difficulty}
          questionCount={questions.length}
        />

        <ScoreDimensions evaluation={evaluation} />

        <FeedbackList
          title="What you did well"
          items={evaluation.strengths}
          icon={CheckIcon}
          iconClassName="bg-accent-soft text-accent"
          emptyMessage="No specific strengths were identified for this interview."
        />

        <FeedbackList
          title="Where to improve"
          items={evaluation.weaknesses}
          icon={TargetIcon}
          iconClassName="bg-line/60 text-ink/60"
          emptyMessage="No specific areas for improvement were identified."
        />

        <EvidenceSection evidence={evaluation.evidence} questions={questions} />

        <QuestionReview questions={questions} />

        <section className="border-t border-line/70">
          <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-14 text-center sm:px-8">
            <Button to="/interview/new" variant="primary" withArrow>
              Practice again
            </Button>
            <Link to="/" className="text-sm font-medium text-ink/60 hover:text-ink hover:underline">
              Back to home
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}

export default InterviewResult
