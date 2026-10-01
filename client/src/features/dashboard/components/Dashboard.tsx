import { ArrowRight } from 'lucide-react'
import AppFrame from '@/features/app/components/AppFrame'
import ResultNotice from '@/features/result/components/ResultNotice'
import { useDashboardData } from '../hooks/useDashboardData'
import { usePageEntrance } from '@/features/app/hooks/usePageEntrance'
import HeroInterview from './HeroInterview'
import RecentResults from './RecentResults'
import Skeleton from './Skeleton'
import StreakSection from './StreakSection'
import SummarySection from './SummarySection'

const CONTENT = 'relative mx-auto max-w-[1120px] px-5 pb-20 pt-8 sm:px-8 md:pt-10 lg:px-10'

/** Fetch -> map -> render. While loading, only neutral placeholders are shown; no data is invented. */
function Dashboard() {
  const { state, retry } = useDashboardData()
  const scope = usePageEntrance(state.status === 'ready')
  const view = state.status === 'ready' ? state.view : null

  return (
    <AppFrame user={view?.user ?? null} active="Dashboard" rootRef={scope}>
      <div className="relative overflow-hidden">
        <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 size-[360px] rounded-full bg-yellow/25 max-sm:-right-20 max-sm:-top-20 max-sm:size-[200px]" />
        <div aria-hidden="true" className="pointer-events-none absolute -right-10 top-24 h-[260px] w-[260px] rounded-full border border-orange/25 max-sm:hidden" />
        <div className={CONTENT}>
          {state.status === 'loading' && (
            <div role="status" aria-label="Loading dashboard" className="flex flex-col gap-5">
              <Skeleton className="h-12 w-3/4" />
              <Skeleton className="h-5 w-1/2" />
              <Skeleton className="mt-8 h-[300px] w-full rounded-[28px]" />
              <Skeleton className="mt-6 h-32 w-full" />
            </div>
          )}
          {state.status === 'error' && (
            <ResultNotice
              title="We couldn’t load your dashboard"
              message="Something went wrong on our side or the connection dropped. Please try again."
              action={{ label: 'Try again', onClick: retry }}
            />
          )}
          {state.status === 'unauthenticated' && (
            <ResultNotice title="Sign in to see your dashboard" message="Your session has ended or you’re not signed in yet." action={{ label: 'Sign in', href: '/signin' }} />
          )}

          {view && (
            <div className="flex flex-col gap-6 lg:gap-8">
              <header data-enter="">
                <h1 className="font-serif text-[36px] leading-[1.06] tracking-[-0.02em] text-ink sm:text-[48px]">{view.greeting}</h1>
                <p className="mt-2 max-w-[520px] text-[16px] leading-[1.5] text-ink/65">Your next technical interview is ready when you are.</p>
              </header>

              <HeroInterview primary={view.primary} />
              <SummarySection items={view.summary} />

              <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-8">
                <StreakSection streak={view.streak} />
                <section data-enter="" aria-labelledby="recent-heading" className="rounded-2xl border border-ink/12 bg-white/60 p-6 sm:p-7">
                  <h2 id="recent-heading" className="text-[11px] font-semibold tracking-[0.2em] text-ink/55">
                    RECENT RESULTS
                  </h2>
                  <RecentResults interviews={view.recentInterviews.slice(0, 3)} />
                  {view.recentInterviews.length > 0 && (
                    <a
                      href="/app/results"
                      className="group mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg text-[14.5px] font-semibold text-ink underline decoration-yellow decoration-2 underline-offset-4 outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow"
                    >
                      View all results <ArrowRight size={15} aria-hidden="true" className="transition-transform duration-200 group-hover:translate-x-1 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0" />
                    </a>
                  )}
                </section>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppFrame>
  )
}

export default Dashboard
