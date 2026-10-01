import AppFrame from '@/features/app/components/AppFrame'
import { usePageEntrance } from '@/features/app/hooks/usePageEntrance'
import ResultNotice from '@/features/result/components/ResultNotice'
import { useInterviewSetup } from '../hooks/useInterviewSetup'
import InterviewSummaryCard from './InterviewSummaryCard'
import MobileStartBar from './MobileStartBar'
import ResumeField from './ResumeField'
import RoleSelector from './RoleSelector'
import SetupHeader from './SetupHeader'
import SetupStep from './SetupStep'

const LAYOUT =
  'mx-auto max-w-[1120px] px-5 pb-[132px] pt-8 sm:px-8 md:pt-10 lg:px-10 lg:pb-20'
const GRID = 'mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start lg:gap-8'

const pulse = 'animate-pulse rounded-[14px] bg-ink/[0.07] motion-reduce:animate-none'

/** Layout-preserving placeholder for the two steps while the catalog loads. */
function StepsSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-6">
      <SetupStep number="01" title="Role" hint="Required · who are you preparing to interview as?" headingId="sk-1">
        <div className="grid grid-cols-1 gap-2 min-[480px]:grid-cols-2">
          {Array.from({ length: 7 }, (_, i) => <div key={i} className={`h-[60px] ${pulse}`} />)}
        </div>
      </SetupStep>
      <SetupStep number="02" title="Resume" hint="Optional · PDF or DOCX · max 5 MB" headingId="sk-r">
        <div className={`h-11 w-40 ${pulse}`} />
      </SetupStep>
    </div>
  )
}

function InterviewSetupPage() {
  const setup = useInterviewSetup()
  const scope = usePageEntrance(setup.status === 'ready')
  const { catalog, role, submit } = setup

  const loading = setup.status === 'loading'
  const ready = setup.status === 'ready' && !!catalog && !!role

  const roleLabel = ready ? role.label : 'Role'
  const resumeLabel = setup.resume ? `Resume: ${setup.resume.name}` : 'No resume · optional'
  const busyLabel = submit.status === 'starting' ? 'Starting…' : submit.status === 'uploading' ? 'Uploading resume…' : 'Setting up…'
  const error = submit.status === 'error' ? submit.message : null
  const locked = setup.busy

  return (
    <AppFrame user={setup.user} active="New interview" rootRef={scope}>
      <div className={LAYOUT}>
        {setup.status === 'error' && (
          <ResultNotice
            title="Couldn’t load interview options."
            message="Please check your connection and try again."
            action={{ label: 'Try again', onClick: setup.retryLoad }}
          />
        )}
        {setup.status === 'unauthenticated' && (
          <ResultNotice
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
                <form onSubmit={(e) => e.preventDefault()} aria-label="Interview setup" className="flex min-w-0 flex-col gap-6">
                  <SetupStep number="01" title="Role" hint="Required · who are you preparing to interview as?" headingId="step-role">
                    <RoleSelector roles={catalog.roles} value={role.value} onChange={setup.selectRole} disabled={locked} />
                  </SetupStep>
                  <SetupStep number="02" title="Resume" hint="Optional · PDF or DOCX · max 5 MB" headingId="step-resume">
                    <ResumeField file={setup.resume} error={setup.resumeError} onChange={setup.chooseResume} disabled={locked} />
                  </SetupStep>
                </form>
              ) : (
                <StepsSkeleton />
              )}

              <InterviewSummaryCard
                roleLabel={roleLabel}
                meta={resumeLabel}
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
                title={roleLabel}
                subtitle={resumeLabel}
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
    </AppFrame>
  )
}

export default InterviewSetupPage
