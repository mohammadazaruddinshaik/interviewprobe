import AppFrame from '@/features/app/components/AppFrame'
import { usePageEntrance } from '@/features/app/hooks/usePageEntrance'
import ResultNotice from '@/features/result/components/ResultNotice'
import { useDashboardData } from '../hooks/useDashboardData'
import ResultsTable from './ResultsTable'
import Skeleton from './Skeleton'

/**
 * The latest completed interviews, from the dashboard data the app already has. The dashboard endpoint returns only
 * the most recent few, so this page says "recent" and does not present itself as a complete archive.
 */
function ResultsPage() {
  const { state, retry } = useDashboardData()
  const view = state.status === 'ready' ? state.view : null
  const scope = usePageEntrance(state.status === 'ready')
  const count = view?.recentInterviews.length ?? 0

  return (
    <AppFrame user={view?.user ?? null} active="Results" rootRef={scope}>
      <div className="mx-auto max-w-[1120px] px-5 pb-20 pt-8 sm:px-8 md:pt-10 lg:px-10">
        {state.status === 'loading' && (
          <div role="status" aria-label="Loading results" className="flex flex-col gap-5">
            <Skeleton className="h-12 w-48" />
            <Skeleton className="h-5 w-72" />
            <Skeleton className="mt-6 h-72 w-full rounded-2xl" />
          </div>
        )}
        {state.status === 'error' && (
          <ResultNotice title="We couldn’t load your results" message="Something went wrong on our side or the connection dropped. Please try again." action={{ label: 'Try again', onClick: retry }} />
        )}
        {state.status === 'unauthenticated' && (
          <ResultNotice title="Sign in to see your results" message="Your session has ended or you’re not signed in yet." action={{ label: 'Sign in', href: '/signin' }} />
        )}
        {view && (
          <div className="flex flex-col gap-6 lg:gap-8">
            <header data-enter="">
              <span aria-hidden="true" className="mb-5 block h-[2px] w-10 bg-orange" />
              <h1 className="font-serif text-[38px] leading-[1.06] tracking-[-0.02em] text-ink sm:text-[50px]">Results</h1>
              <p className="mt-2 text-[16px] text-ink/65">Your recent interview reflections.</p>
            </header>
            {count > 0 ? (
              <>
                <p data-enter="" className="text-[13.5px] text-ink/55">
                  Latest {count} completed {count === 1 ? 'interview' : 'interviews'}
                </p>
                <ResultsTable interviews={view.recentInterviews} />
              </>
            ) : (
              <section data-enter="" className="rounded-2xl border border-ink/12 bg-white/60 p-8">
                <p className="text-[17px] text-ink">No completed interviews yet.</p>
                <a
                  href="/app/interviews/new"
                  className="mt-4 inline-flex min-h-11 items-center rounded-lg text-[14.5px] font-semibold text-ink underline decoration-yellow decoration-2 underline-offset-4 outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow"
                >
                  Start an interview →
                </a>
              </section>
            )}
          </div>
        )}
      </div>
    </AppFrame>
  )
}

export default ResultsPage
