import { ArrowRight } from 'lucide-react'
import type { RecentInterviewView } from '../data/dashboardViewModel'
import Skeleton from './Skeleton'

function RecentInterviews({ interviews, loading }: { interviews: RecentInterviewView[]; loading: boolean }) {
  const show = (text: string) => (loading ? <Skeleton>{text}</Skeleton> : text)

  return (
    <section data-dash="recent" aria-labelledby="recent-heading" aria-busy={loading}>
      <div className="flex items-baseline justify-between">
        <h2 id="recent-heading" className="font-display text-[22px] font-extrabold tracking-[-0.02em] text-deep">
          Recent Interviews
        </h2>
        <a href="#interviews" className="group inline-flex items-center gap-1.5 rounded-sm text-[13.5px] font-semibold text-forest outline-offset-4 focus-visible:outline-2 focus-visible:outline-forest">
          View All
          <ArrowRight size={15} aria-hidden="true" className="transition-transform duration-200 group-hover:translate-x-[3px] motion-reduce:transition-none motion-reduce:group-hover:translate-x-0" />
        </a>
      </div>

      {!loading && interviews.length === 0 ? (
        <div className="mt-4 border-y border-ink/10 px-2 py-8">
          <p className="text-[15px] font-semibold text-deep">No completed interviews yet</p>
          <p className="mt-1 text-[13px] text-ink/55">Finish an interview and your results will show up here.</p>
        </div>
      ) : (
        <ul className="mt-4 border-t border-ink/10">
          {interviews.map((item) => (
            <li key={item.id} className="border-b border-ink/10">
              <a
                href={item.href}
                aria-disabled={loading || undefined}
                tabIndex={loading ? -1 : undefined}
                className={`group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 rounded-lg px-2 py-4 outline-offset-[-2px] transition-colors duration-200 hover:bg-forest/[0.035] focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none sm:grid-cols-[minmax(0,1fr)_84px_56px_120px_20px] sm:gap-x-5 ${loading ? 'pointer-events-none' : ''}`}
              >
                <span className="min-w-0">
                  <span className="block truncate text-[15px] font-semibold text-deep">{show(item.role)}</span>
                  <span className="mt-0.5 block truncate text-[13px] text-ink/55">{show(item.focus)}</span>
                </span>
                <span className="hidden w-fit rounded-full border border-ink/12 px-2.5 py-0.5 text-[11.5px] font-medium text-ink/65 sm:block">
                  {show(item.difficulty)}
                </span>
                <span className="text-right font-display text-[16px] font-extrabold tabular-nums text-deep sm:text-left">
                  {item.score === null ? (
                    <span title="No evaluation yet" className="text-ink/35">—</span>
                  ) : (
                    show(item.score)
                  )}
                </span>
                <span className="col-span-2 text-[12.5px] text-ink/50 sm:col-span-1 sm:text-[13px]">
                  <span className="sm:hidden">{item.difficulty} · </span>
                  {show(item.date)}
                </span>
                <ArrowRight size={16} aria-hidden="true" className="hidden text-ink/35 transition-[translate,color] duration-200 group-hover:translate-x-[3px] group-hover:text-forest motion-reduce:transition-none motion-reduce:group-hover:translate-x-0 sm:block" />
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default RecentInterviews
