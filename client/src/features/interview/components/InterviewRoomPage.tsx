import AppShell from '@/features/app/components/AppShell'
import DashboardNotice from '@/features/dashboard/components/DashboardNotice'
import DashboardSidebar from '@/features/dashboard/components/DashboardSidebar'
import DashboardTopBar from '@/features/dashboard/components/DashboardTopBar'
import { difficultyLabel, roleLabel } from '@/features/dashboard/lib/labels'
import { useInterviewRoom } from '../hooks/useInterviewRoom'
import { useRetryCountdown } from '../hooks/useRetryCountdown'
import { useRoomEntrance } from '../hooks/useRoomEntrance'
import { questionProgress } from '../lib/progress'
import { sendButtonState } from '../lib/sendState'
import AnswerComposer from './AnswerComposer'
import EndInterviewDialog from './EndInterviewDialog'
import MobileSendBar from './MobileSendBar'
import QuestionPanel from './QuestionPanel'
import RoomHeader from './RoomHeader'
import RoomSkeleton from './RoomSkeleton'
import TopicRoadmap from './TopicRoadmap'

const LAYOUT = 'mx-auto max-w-[1180px] px-4 pb-[132px] pt-5 sm:px-6 sm:pt-7 lg:px-8 lg:pb-16 lg:pt-8 xl:px-10'
const GRID = 'mt-7 grid gap-8 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-10'

function InterviewRoomPage({ interviewId }: { interviewId: string }) {
  const room = useInterviewRoom(interviewId)
  const { state } = room
  const questionId = state.phase === 'ready' ? state.question.id : null
  const scope = useRoomEntrance(state.phase, questionId)
  const until = state.phase === 'ready' && state.turn.status === 'rateLimited' ? state.turn.until : null
  const secondsLeft = useRetryCountdown(until)

  return (
    <AppShell
      rootRef={scope}
      sidebar={(mode, close) => <DashboardSidebar mode={mode} close={close} />}
      topBar={(controls) => <DashboardTopBar userName={room.userName ?? 'Account'} context="Interview" {...controls} />}
    >
      <div className={LAYOUT}>
        {state.phase === 'loading' && <RoomSkeleton />}

        {state.phase === 'notFound' && (
          <DashboardNotice title="Interview not found" message="We couldn’t find that interview. It may not exist, or it may belong to a different account." action={{ label: 'Back to dashboard', href: '/app' }} />
        )}
        {state.phase === 'unauthenticated' && (
          <DashboardNotice title="You’re signed out" message="Your session has ended. Sign in again to continue your interview." action={{ label: 'Sign in', href: '/signin' }} />
        )}
        {state.phase === 'loadError' && (
          <DashboardNotice title="Couldn’t load your interview" message="Please check your connection and try again." action={{ label: 'Try again', onClick: room.reload }} />
        )}
        {state.phase === 'notStarted' && (
          <DashboardNotice title="This interview hasn’t started" message="Set up a new interview to begin." action={{ label: 'Set up an interview', href: '/app/interviews/new' }} />
        )}
        {state.phase === 'failed' && (
          <DashboardNotice title="This interview couldn’t continue" message="Something went wrong with this interview. You can start a new one." action={{ label: 'Set up an interview', href: '/app/interviews/new' }} />
        )}

        {state.phase === 'completed' && (
          <p role="status" className="font-serif text-[17px] text-ink/70">
            Interview complete. Opening your results…
          </p>
        )}

        {state.phase === 'ready' && (() => {
          const progress = questionProgress(state.question, state.interview.question_limit)
          const button = sendButtonState(state.draft, state.attempt, state.turn, secondsLeft)
          return (
            <>
              <RoomHeader
                roleLabel={roleLabel(state.interview.role)}
                difficultyLabel={difficultyLabel(state.interview.difficulty)}
                current={progress.current}
                total={progress.total}
                onEnd={room.openEnd}
                endDisabled={state.turn.status === 'submitting'}
              />
              <div className={GRID}>
                <div className="flex min-w-0 flex-col gap-6">
                  <QuestionPanel question={state.question} />
                  <AnswerComposer
                    draft={state.draft}
                    attempt={state.attempt}
                    turn={state.turn}
                    secondsLeft={secondsLeft}
                    onChange={room.setDraft}
                    onSubmit={room.submit}
                  />
                </div>
                <TopicRoadmap topics={state.interview.topics} transcript={state.transcript} />
              </div>
              <MobileSendBar label={button.label} busy={button.busy} disabled={button.disabled} characters={state.draft.length} onSend={room.submit} />
              <EndInterviewDialog flow={state.endFlow} onCancel={room.closeEnd} onConfirm={room.confirmEnd} />
            </>
          )
        })()}
      </div>
    </AppShell>
  )
}

export default InterviewRoomPage
