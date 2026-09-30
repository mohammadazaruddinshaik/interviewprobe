import AppShell from '@/features/app/components/AppShell'
import DashboardNotice from '@/features/dashboard/components/DashboardNotice'
import DashboardSidebar from '@/features/dashboard/components/DashboardSidebar'
import DashboardTopBar from '@/features/dashboard/components/DashboardTopBar'
import { useInterviewSetup } from '../hooks/useInterviewSetup'
import { useSetupEntrance } from '../hooks/useSetupEntrance'
import { difficultyCopy } from '../lib/copy'
import DifficultySelector from './DifficultySelector'
import FocusTopics from './FocusTopics'
import InterviewSummaryCard from './InterviewSummaryCard'
import MobileStartBar from './MobileStartBar'
import QuestionCountSelector from './QuestionCountSelector'
import RoleSelector from './RoleSelector'
import SetupHeader from './SetupHeader'
import SetupStep from './SetupStep'

const LAYOUT =
  'mx-auto max-w-[1180px] px-4 pb-[132px] pt-5 sm:px-6 sm:pt-7 lg:px-8 lg:pb-16 lg:pt-10 xl:px-10 xl:pb-[72px] xl:pt-12'
const GRID = 'mt-8 grid gap-9 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start lg:gap-8 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-12'

const pulse = 'animate-pulse rounded-[14px] bg-ink/[0.07] motion-reduce:animate-none'

/** Layout-preserving placeholder for the four steps while the catalog loads. */
function StepsSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-[34px]">
      <SetupStep number="01" title="Role" hint="Who are you preparing to interview as?" headingId="sk-1">
        <div className="grid grid-cols-1 gap-2 min-[480px]:grid-cols-2">
          {Array.from({ length: 7 }, (_, i) => <div key={i} className={`h-[60px] ${pulse}`} />)}
        </div>
      </SetupStep>
      <SetupStep number="02" title="Difficulty" hint="How hard should the questions get?" headingId="sk-2">
        <div className="grid grid-cols-3 gap-2">{[0, 1, 2].map((i) => <div key={i} className={`h-16 ${pulse}`} />)}</div>
      </SetupStep>
      <SetupStep number="03" title="Focus areas" hint="Pick what you want to be asked about." headingId="sk-3">
        <div className="flex flex-wrap gap-2">
          {[130, 70, 170, 100, 120, 140].map((w, i) => <div key={i} style={{ width: w }} className={`h-11 !rounded-full ${pulse}`} />)}
        </div>
      </SetupStep>
      <SetupStep number="04" title="Questions" hint="How many would you like to be asked?" headingId="sk-4">
        <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">{Array.from({ length: 8 }, (_, i) => <div key={i} className={`h-12 ${pulse}`} />)}</div>
      </SetupStep>
    </div>
  )
}

function InterviewSetupPage() {
  const setup = useInterviewSetup()
  const scope = useSetupEntrance(setup.status === 'ready')
  const { catalog, selection, role, submit } = setup

  const loading = setup.status === 'loading'
  const ready = setup.status === 'ready' && !!catalog && !!selection && !!role

  const topicLabels = ready ? selection.topics.map((v) => role.topics.find((t) => t.value === v)?.label ?? v) : []
  const difficultyLabel = ready ? difficultyCopy(selection.difficulty).label : ''
  const meta = ready ? `${difficultyLabel} · ${selection.questionLimit} questions` : 'Medium · 5 questions'
  const roleLabel = ready ? role.label : 'Role'
  const busyLabel = submit.status === 'starting' ? 'Starting…' : 'Setting up…'
  const error = submit.status === 'error' ? submit.message : null
  const locked = setup.busy

  return (
    <AppShell
      rootRef={scope}
      sidebar={(mode, close) => <DashboardSidebar mode={mode} close={close} />}
      topBar={(controls) => <DashboardTopBar userName={setup.user?.name ?? 'Account'} context="New interview" {...controls} />}
    >
      <div className={LAYOUT}>
        {setup.status === 'error' && (
          <DashboardNotice
            title="Couldn’t load interview options."
            message="Please check your connection and try again."
            action={{ label: 'Try again', onClick: setup.retryLoad }}
          />
        )}
        {setup.status === 'unauthenticated' && (
          <DashboardNotice
            title="Sign in to set up an interview"
            message="Your session has ended or you’re not signed in yet."
            action={{ label: 'Sign in', href: '/signin' }}
          />
        )}

        {(loading || ready) && (
          <>
            <SetupHeader />
            <div className={GRID}>
              {ready ? (
                <form onSubmit={(e) => e.preventDefault()} aria-label="Interview setup" className="flex min-w-0 flex-col gap-[34px]">
                  <SetupStep number="01" title="Role" hint="Who are you preparing to interview as?" headingId="step-role">
                    <RoleSelector roles={catalog.roles} value={selection.role} onChange={setup.selectRole} disabled={locked} />
                  </SetupStep>
                  <SetupStep number="02" title="Difficulty" hint="How hard should the questions get?" headingId="step-difficulty">
                    <DifficultySelector
                      difficulties={catalog.difficulties.map((d) => d.value)}
                      value={selection.difficulty}
                      onChange={setup.selectDifficulty}
                      disabled={locked}
                    />
                  </SetupStep>
                  <SetupStep number="03" title="Focus areas" hint="Pick what you want to be asked about." headingId="step-topics">
                    <FocusTopics
                      topics={role.topics}
                      selected={selection.topics}
                      cap={setup.topicCap}
                      min={catalog.topic_limit.min}
                      max={catalog.topic_limit.max}
                      onToggle={setup.toggleTopic}
                      disabled={locked}
                    />
                  </SetupStep>
                  <SetupStep number="04" title="Questions" hint="How many would you like to be asked?" headingId="step-questions">
                    <QuestionCountSelector
                      min={catalog.question_limit.min}
                      max={catalog.question_limit.max}
                      value={selection.questionLimit}
                      onChange={setup.selectQuestionLimit}
                      disabled={locked}
                    />
                  </SetupStep>
                </form>
              ) : (
                <StepsSkeleton />
              )}

              <InterviewSummaryCard
                roleLabel={roleLabel}
                meta={meta}
                topicLabels={topicLabels}
                canSubmit={setup.canSubmit}
                busy={setup.busy}
                busyLabel={busyLabel}
                error={error}
                loading={loading}
                onStart={setup.submitSetup}
              />
            </div>
            {ready && (
              <MobileStartBar
                title={`${roleLabel} · ${difficultyLabel} · ${selection.questionLimit} questions`}
                subtitle={topicLabels.length > 0 ? topicLabels.join(' · ') : 'Choose a focus area'}
                canSubmit={setup.canSubmit}
                busy={setup.busy}
                busyLabel={busyLabel}
                error={error}
                onStart={setup.submitSetup}
              />
            )}
          </>
        )}
      </div>
    </AppShell>
  )
}

export default InterviewSetupPage
