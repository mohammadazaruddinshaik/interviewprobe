import AppShell from '@/features/app/components/AppShell'
import { CONTINUE_LEARNING } from '../content/staticContent'
import { LOADING_VIEW } from '../data/loadingView'
import { useDashboardData } from '../hooks/useDashboardData'
import { useDashboardEntrance } from '../hooks/useDashboardEntrance'
import ContinueLearning from './ContinueLearning'
import DashboardNotice from './DashboardNotice'
import DashboardSidebar from './DashboardSidebar'
import DashboardTopBar from './DashboardTopBar'
import NextInterviewCard from './NextInterviewCard'
import PracticeStreak from './PracticeStreak'
import PracticedTopics from './PracticedTopics'
import RecentInterviews from './RecentInterviews'
import StatsRow from './StatsRow'
import WelcomeHeader from './WelcomeHeader'

const LAYOUT =
  'mx-auto grid max-w-[1180px] gap-8 px-4 pb-16 pt-6 md:gap-10 md:px-6 md:pt-10 lg:grid-cols-[minmax(0,1fr)_256px] lg:gap-x-7 lg:px-8 xl:grid-cols-[minmax(0,1fr)_316px] xl:gap-x-10 xl:px-10'

/** Coordinates fetch -> map -> render. Presentational components only receive display-ready data. */
function Dashboard() {
  const scope = useDashboardEntrance()
  const { state, retry } = useDashboardData()

  const loading = state.status === 'loading'
  const view = state.status === 'ready' ? state.view : LOADING_VIEW

  return (
    <AppShell
      rootRef={scope}
      sidebar={(mode, close) => <DashboardSidebar mode={mode} close={close} />}
      topBar={(controls) => <DashboardTopBar userName={view.userName} {...controls} />}
    >
      <div className={LAYOUT}>
        {state.status === 'error' && (
          <DashboardNotice
            title="We couldn’t load your dashboard"
            message="Something went wrong on our side or the connection dropped. Please try again."
            action={{ label: 'Try again', onClick: retry }}
          />
        )}
        {state.status === 'unauthenticated' && (
          <DashboardNotice
            title="Sign in to see your dashboard"
            message="Your session has ended or you’re not signed in yet."
            action={{ label: 'Sign in', href: '/signin' }}
          />
        )}

        {(state.status === 'loading' || state.status === 'ready') && (
          <>
            <div className="flex min-w-0 flex-col gap-6 sm:gap-8 md:gap-10">
              <WelcomeHeader greeting={view.greeting} loading={loading} />
              <NextInterviewCard interview={view.nextInterview} loading={loading} />
              <StatsRow stats={view.stats} loading={loading} />
              <RecentInterviews interviews={view.recentInterviews} loading={loading} />
            </div>

            <aside aria-label="Progress" className="flex min-w-0 flex-col gap-4 lg:pt-[6px]">
              <PracticeStreak streak={view.streak} loading={loading} />
              <PracticedTopics topics={view.practicedTopics} loading={loading} />
              {/* Static product content: not fetched, no backend API exists for it yet. */}
              <ContinueLearning items={CONTINUE_LEARNING} />
            </aside>
          </>
        )}
      </div>
    </AppShell>
  )
}

export default Dashboard
