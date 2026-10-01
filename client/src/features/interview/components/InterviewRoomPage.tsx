import DashboardNotice from '@/features/dashboard/components/DashboardNotice'
import { useInterviewRoom } from '../hooks/useInterviewRoom'
import { useRoomEntrance } from '../hooks/useRoomEntrance'
import RoomSkeleton from './RoomSkeleton'
import StartPrompt from './StartPrompt'
import VoiceRoom from './VoiceRoom'

const NOTICE_LAYOUT = 'mx-auto max-w-[760px] px-4 py-10 sm:px-6'

/** The voice-first interview room. Server state is authoritative; this page only chooses what to show. */
function InterviewRoomPage({ interviewId }: { interviewId: string }) {
  const room = useInterviewRoom(interviewId)
  const { state } = room
  const scope = useRoomEntrance(state.phase, state.phase === 'ready' ? state.question.id : null)

  return (
    <div ref={scope} className={`min-h-screen ${state.phase === 'ready' || state.phase === 'loading' || state.phase === 'notStarted' ? 'bg-[#06110a] text-cream' : 'bg-cream text-ink'}`}>
      {state.phase === 'loading' && <RoomSkeleton />}

      <div className={state.phase === 'ready' || state.phase === 'loading' ? undefined : NOTICE_LAYOUT}>
        {state.phase === 'notFound' && (
          <DashboardNotice title="Interview not found" message="We couldn’t find that interview. It may not exist, or it may belong to a different account." action={{ label: 'Back to dashboard', href: '/app' }} />
        )}
        {state.phase === 'unauthenticated' && (
          <DashboardNotice title="You’re signed out" message="Your session has ended. Sign in again to continue your interview." action={{ label: 'Sign in', href: '/signin' }} />
        )}
        {state.phase === 'loadError' && (
          <DashboardNotice title="Couldn’t load your interview" message="Please check your connection and try again." action={{ label: 'Try again', onClick: room.reload }} />
        )}
        {state.phase === 'notStarted' && <StartPrompt interviewId={interviewId} />}
        {state.phase === 'failed' && (
          <DashboardNotice title="This interview couldn’t continue" message="Something went wrong with this interview. You can start a new one." action={{ label: 'Set up an interview', href: '/app/interviews/new' }} />
        )}
        {state.phase === 'completed' && (
          <div data-room="completed" role="status" className="flex min-h-[50vh] flex-col items-center justify-center text-center">
            <h1 className="font-display text-[28px] font-extrabold leading-[1.1] tracking-[-0.025em] text-deep sm:text-[34px]">Interview complete.</h1>
            <p className="mt-3 font-serif text-[17px] text-ink/60">Opening your results…</p>
          </div>
        )}
      </div>

      {state.phase === 'ready' && <VoiceRoom state={state} room={room} />}
    </div>
  )
}

export default InterviewRoomPage
