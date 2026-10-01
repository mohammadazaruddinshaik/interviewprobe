import { ArrowRight } from 'lucide-react'
import type { RecentInterviewView } from '../data/dashboardViewModel'

/** Compact list for the dashboard panel: role, date and score only, each row opening its result. */
function RecentResults({ interviews }: { interviews: RecentInterviewView[] }) {
  if (interviews.length === 0) {
    return (
      <div className="mt-5">
        <p className="text-[16px] text-ink">No completed interviews yet.</p>
        <a
          href="/app/interviews/new"
          className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg text-[14.5px] font-semibold text-ink underline decoration-yellow decoration-2 underline-offset-4 outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow"
        >
          Start an interview <ArrowRight size={15} aria-hidden="true" />
        </a>
      </div>
    )
  }
  return (
    <ul className="mt-4 divide-y divide-ink/10 border-t border-ink/10">
      {interviews.map((item) => (
        <li key={item.id}>
          <a
            href={item.href}
            className="group relative -mx-3 flex items-center justify-between gap-4 rounded-lg px-3 py-4 outline-offset-[-2px] transition-colors duration-200 hover:bg-yellow/20 focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none"
          >
            <span aria-hidden="true" className="absolute left-0 top-1/2 h-0 w-[3px] -translate-y-1/2 bg-orange transition-[height] duration-200 group-hover:h-7 motion-reduce:transition-none" />
            <span className="min-w-0">
              <span className="block truncate font-serif text-[20px] leading-tight text-ink">{item.role}</span>
              <span className="mt-0.5 block text-[13px] text-ink/60">{item.completed}</span>
            </span>
            <span className="flex shrink-0 items-center gap-3">
              {item.score ? <span className="font-serif text-[22px] text-ink">{item.score}</span> : <span className="text-[13px] text-ink/50">Score unavailable</span>}
              <ArrowRight size={15} aria-hidden="true" className="text-ink/40 transition-[translate,color] duration-200 group-hover:translate-x-[3px] group-hover:text-ink motion-reduce:transition-none motion-reduce:group-hover:translate-x-0" />
            </span>
          </a>
        </li>
      ))}
    </ul>
  )
}

export default RecentResults
