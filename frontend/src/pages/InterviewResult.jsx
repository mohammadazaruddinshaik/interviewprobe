import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { getInterviewResult } from '../api/interviews.js'
import EvidenceSection from '../components/result/EvidenceSection.jsx'
import FeedbackSection from '../components/result/FeedbackSection.jsx'
import InterviewSummary from '../components/result/InterviewSummary.jsx'
import NextSteps from '../components/result/NextSteps.jsx'
import OverallScoreCard from '../components/result/OverallScoreCard.jsx'
import QuestionBreakdown from '../components/result/QuestionBreakdown.jsx'
import ResultLoading from '../components/result/ResultLoading.jsx'
import ResultsHeader from '../components/result/ResultsHeader.jsx'
import ResultsNavbar from '../components/result/ResultsNavbar.jsx'
import ResultsShell from '../components/result/ResultsShell.jsx'
import ScoreBreakdown from '../components/result/ScoreBreakdown.jsx'
import InterviewError from '../components/interview/InterviewError.jsx'
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

  // Every phase renders inside the same navbar + glass shell, so the
  // route reads as one consistent product surface (matching Landing,
  // Setup, and Interview) rather than the error/loading states looking
  // like a different, unstyled page.
  return (
    <div className="text-ink">
      <div className="px-3 py-3 sm:px-5 sm:py-5 lg:px-8 lg:py-6">
        <ResultsShell>
          <ResultsNavbar />

          {phase === 'loading' && <ResultLoading />}

          {phase === 'incomplete' && (
            <InterviewError message={INCOMPLETE_MESSAGE}>
              <Link
                to={`/interview/${sessionId}`}
                className="mt-4 inline-block text-sm font-medium text-accent hover:underline"
              >
                Continue interview
              </Link>
            </InterviewError>
          )}

          {phase === 'error' && (
            <InterviewError message={loadError ?? GENERIC_LOAD_ERROR} onRetry={handleRetry}>
              <Link to="/" className="mt-4 inline-block text-sm font-medium text-accent hover:underline">
                Back to home
              </Link>
            </InterviewError>
          )}

          {phase === 'ready' && <ReadyResult result={result} />}
        </ResultsShell>
      </div>
    </div>
  )
}

// Split out purely so the destructuring below doesn't have to guard
// against `result` being null during the other phases.
function ReadyResult({ result }) {
  const { interview, questions, evaluation } = result
  const roleLabel = ROLE_LABELS[interview.role] ?? interview.role
  const difficultyLabel = DIFFICULTY_LABELS[interview.difficulty] ?? interview.difficulty

  // The one combined "role · difficulty · question count" line — shown
  // once, in OverallScoreCard, alongside the score; InterviewSummary below
  // shows the same facts broken out individually (date, duration, count,
  // difficulty) for a fuller read. Real fields only, in the fixed order
  // this page has always used.
  const metaLine = [roleLabel, difficultyLabel, `${questions.length} question${questions.length === 1 ? '' : 's'}`]
    .filter(Boolean)
    .join(' · ')

  return (
    <>
      <ResultsHeader />

      {/* The reference's report layout: a wide left column (the session,
          the four dimensions, the written feedback) beside a narrower right
          column (the overall score, then every question asked, then the
          evaluator's evidence).
          Below `lg` the two column wrappers become `display: contents`, so
          their cards join this one flex column and `order-*` sets the
          mobile reading order: score first, then summary, breakdown,
          feedback, questions, evidence. At `lg` the wrappers are real
          columns again and `lg:order-none` restores natural order. */}
      <main className="flex flex-col gap-4 px-4 pb-10 pt-4 sm:px-6 sm:pb-12 lg:grid lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)] lg:items-start lg:gap-5 lg:px-8">
        <div className="contents lg:flex lg:min-w-0 lg:flex-col lg:gap-5">
          <InterviewSummary
            roleLabel={roleLabel}
            difficultyLabel={difficultyLabel}
            startedAt={interview.started_at}
            completedAt={interview.completed_at}
            questionCount={questions.length}
            className="order-2 lg:order-none"
          />
          <ScoreBreakdown evaluation={evaluation} className="order-3 lg:order-none" />
          <FeedbackSection
            strengths={evaluation.strengths}
            weaknesses={evaluation.weaknesses}
            className="order-4 lg:order-none"
          />
        </div>

        <div className="contents lg:flex lg:min-w-0 lg:flex-col lg:gap-5">
          <OverallScoreCard overallScore={evaluation.overall_score} metaLine={metaLine} className="order-1 lg:order-none" />
          <QuestionBreakdown questions={questions} className="order-5 lg:order-none" />
          <EvidenceSection evidence={evaluation.evidence} questions={questions} className="order-6 lg:order-none" />
        </div>

        <div className="order-7 lg:col-span-2">
          <NextSteps />
        </div>
      </main>
    </>
  )
}

export default InterviewResult
