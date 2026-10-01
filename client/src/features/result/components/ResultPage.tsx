import { useCallback } from 'react'
import AppFrame from '@/features/app/components/AppFrame'
import { usePageEntrance } from '@/features/app/hooks/usePageEntrance'
import { useInterviewResult } from '../hooks/useInterviewResult'
import DimensionScores from './DimensionScores'
import EvaluatingState from './EvaluatingState'
import EvidenceList from './EvidenceList'
import FeedbackColumns from './FeedbackColumns'
import OverallScoreCard from './OverallScoreCard'
import QuestionReview from './QuestionReview'
import ResultActions from './ResultActions'
import ResultHeader from './ResultHeader'
import ResultNotice from './ResultNotice'
import ResultSkeleton from './ResultSkeleton'
import TopicCoverage from './TopicCoverage'

/** The interview report: one centred reading column on the same dark canvas as the room. */
function ResultPage({ interviewId }: { interviewId: string }) {
  const { state, user, retry } = useInterviewResult(interviewId)
  const scope = usePageEntrance(state.phase === 'ready')

  const viewQuestion = useCallback((id: string) => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
    document.getElementById(`q-${id}`)?.scrollIntoView({ block: 'center', behavior: reduced ? 'auto' : 'smooth' })
    document.getElementById(`q-heading-${id}`)?.focus({ preventScroll: true })
  }, [])

  let body
  switch (state.phase) {
    case 'loading':
      body = <ResultSkeleton />
      break
    case 'evaluating':
      body = <EvaluatingState />
      break
    case 'notFound':
      body = <ResultNotice title="Interview not found." message="We couldn’t find that interview. It may not exist, or it may belong to a different account." action={{ label: 'Back to dashboard', href: '/app' }} />
      break
    case 'unauthenticated':
      body = <ResultNotice title="You’re signed out" message="Your session has ended. Sign in again to see your results." action={{ label: 'Sign in', href: '/signin' }} />
      break
    case 'notCompleted':
      body =
        state.status === 'IN_PROGRESS' ? (
          <ResultNotice title="This interview isn’t finished yet" message="Results are available once the interview is complete." action={{ label: 'Continue interview', href: `/app/interviews/${encodeURIComponent(interviewId)}` }} />
        ) : state.status === 'CREATED' ? (
          <ResultNotice title="This interview hasn’t started" message="Set up an interview to begin." action={{ label: 'Set up an interview', href: '/app/interviews/new' }} />
        ) : state.status === 'FAILED' ? (
          <ResultNotice title="This interview couldn’t continue" message="There are no results for this interview. You can start a new one." action={{ label: 'Start a new interview', href: '/app/interviews/new' }} />
        ) : (
          <ResultNotice title="Results aren’t available yet" message="We couldn’t confirm the state of this interview. Please try again." action={{ label: 'Try again', onClick: retry }} />
        )
      break
    case 'failed':
      body =
        state.reason === 'evaluation' ? (
          <ResultNotice title="Your interview is complete, but we couldn’t prepare the reflection." message="Nothing was lost, and trying again is safe." action={{ label: 'Try again', onClick: retry }} />
        ) : (
          <ResultNotice title="We couldn’t load your results" message="Please check your connection and try again." action={{ label: 'Try again', onClick: retry }} />
        )
      break
    case 'ready': {
      const { result } = state
      const knownIds = new Set(result.questions.map((q) => q.id))
      body = (
        <>
          <ResultHeader result={result} />
          <OverallScoreCard score={result.evaluation.overall_score} />
          <DimensionScores evaluation={result.evaluation} />
          <FeedbackColumns evaluation={result.evaluation} />
          <EvidenceList evidence={result.evaluation.evidence} knownQuestionIds={knownIds} onViewQuestion={viewQuestion} />
          <TopicCoverage topics={result.topics} />
          <QuestionReview questions={result.questions} />
          <ResultActions />
        </>
      )
    }
  }

  return (
    <AppFrame user={user} active="Results" rootRef={scope}>
      <div className="mx-auto max-w-[1120px] px-5 pb-20 pt-8 sm:px-8 md:pt-10 lg:px-10">
        {state.phase === 'ready' ? <div className="flex flex-col gap-6 lg:gap-8">{body}</div> : body}
      </div>
    </AppFrame>
  )
}

export default ResultPage
