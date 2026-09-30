import { useCallback, useState } from 'react'
import AppShell from '@/features/app/components/AppShell'
import DashboardNotice from '@/features/dashboard/components/DashboardNotice'
import DashboardSidebar from '@/features/dashboard/components/DashboardSidebar'
import DashboardTopBar from '@/features/dashboard/components/DashboardTopBar'
import { useInterviewResult } from '../hooks/useInterviewResult'
import { useResultEntrance } from '../hooks/useResultEntrance'
import DimensionScores from './DimensionScores'
import EvaluatingState from './EvaluatingState'
import EvidenceList from './EvidenceList'
import FeedbackColumns from './FeedbackColumns'
import OverallScoreCard from './OverallScoreCard'
import QuestionReview from './QuestionReview'
import ResultHeader from './ResultHeader'
import ResultSkeleton from './ResultSkeleton'
import ResultSummaryRail from './ResultSummaryRail'
import TopicCoverage from './TopicCoverage'

const LAYOUT = 'mx-auto max-w-[1180px] px-4 pb-16 pt-6 sm:px-6 sm:pt-8 lg:px-8 lg:pt-10 xl:px-10 xl:pt-12'
const GRID = 'grid gap-10 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-12'

function ResultPage({ interviewId }: { interviewId: string }) {
  const { state, userName, retry } = useInterviewResult(interviewId)
  const scope = useResultEntrance(state.phase === 'ready')
  const [openIds, setOpenIds] = useState<Set<string>>(() => new Set())

  const toggle = useCallback((id: string) => {
    setOpenIds((current) => {
      const next = new Set(current)
      if (!next.delete(id)) next.add(id)
      return next
    })
  }, [])

  const viewQuestion = useCallback((id: string) => {
    setOpenIds((current) => new Set(current).add(id))
    // Move focus to that question's disclosure button once it has rendered open.
    requestAnimationFrame(() => {
      const button = document.getElementById(`q-btn-${id}`)
      button?.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
      button?.focus({ preventScroll: true })
    })
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
      body = <DashboardNotice title="Interview not found." message="We couldn’t find that interview. It may not exist, or it may belong to a different account." action={{ label: 'Back to dashboard', href: '/app' }} />
      break
    case 'unauthenticated':
      body = <DashboardNotice title="You’re signed out" message="Your session has ended. Sign in again to see your results." action={{ label: 'Sign in', href: '/signin' }} />
      break
    case 'notCompleted':
      body =
        state.status === 'IN_PROGRESS' ? (
          <DashboardNotice title="This interview isn’t finished yet" message="Results are available once the interview is complete." action={{ label: 'Continue interview', href: `/app/interviews/${encodeURIComponent(interviewId)}` }} />
        ) : state.status === 'CREATED' ? (
          <DashboardNotice title="This interview hasn’t started" message="Set up an interview to begin." action={{ label: 'Set up an interview', href: '/app/interviews/new' }} />
        ) : state.status === 'FAILED' ? (
          <DashboardNotice title="This interview couldn’t continue" message="There are no results for this interview. You can start a new one." action={{ label: 'Start a new interview', href: '/app/interviews/new' }} />
        ) : (
          <DashboardNotice title="Results aren’t available yet" message="We couldn’t confirm the state of this interview. Please try again." action={{ label: 'Try again', onClick: retry }} />
        )
      break
    case 'failed':
      body =
        state.reason === 'evaluation' ? (
          <DashboardNotice title="Your interview is complete, but we couldn’t prepare the evaluation." message="Nothing was lost, and trying again is safe." action={{ label: 'Try again', onClick: retry }} />
        ) : (
          <DashboardNotice title="We couldn’t load your results" message="Please check your connection and try again." action={{ label: 'Try again', onClick: retry }} />
        )
      break
    case 'ready': {
      const { result } = state
      const knownIds = new Set(result.questions.map((q) => q.id))
      body = (
        <>
          <div className={GRID}>
            <div className="flex min-w-0 flex-col gap-10">
              <ResultHeader result={result} />
              <OverallScoreCard score={result.evaluation.overall_score} />
              <DimensionScores evaluation={result.evaluation} />
              <FeedbackColumns evaluation={result.evaluation} />
              <EvidenceList evidence={result.evaluation.evidence} knownQuestionIds={knownIds} onViewQuestion={viewQuestion} />
              <TopicCoverage topics={result.topics} />
              <QuestionReview
                questions={result.questions}
                evidence={result.evaluation.evidence}
                openIds={openIds}
                onToggle={toggle}
                onSetAll={(open) => setOpenIds(open ? new Set(result.questions.map((q) => q.id)) : new Set())}
              />
            </div>
            <ResultSummaryRail result={result} />
          </div>
        </>
      )
    }
  }

  return (
    <AppShell
      rootRef={scope}
      sidebar={(mode, close) => <DashboardSidebar mode={mode} close={close} />}
      topBar={(controls) => <DashboardTopBar userName={userName ?? 'Account'} context="Results" {...controls} />}
    >
      <div className={LAYOUT}>{body}</div>
    </AppShell>
  )
}

export default ResultPage
