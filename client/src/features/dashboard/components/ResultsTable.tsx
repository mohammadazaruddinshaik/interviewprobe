import { ArrowRight } from 'lucide-react'
import type { RecentInterviewView } from '../data/dashboardViewModel'

/** Structured results table: clear columns on wide screens, stacked rows on small ones. Every row is one link. */
function ResultsTable({ interviews }: { interviews: RecentInterviewView[] }) {
  return (
    <div data-enter="" className="overflow-hidden rounded-2xl border border-ink/12 bg-white/60">
      <div aria-hidden="true" className="hidden gap-4 border-b border-ink/10 bg-ink/[0.03] px-6 py-3 text-[11px] font-semibold tracking-[0.18em] text-ink/55 sm:grid sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_120px_28px]">
        <span>ROLE</span>
        <span>COMPLETED</span>
        <span className="text-right">SCORE</span>
        <span />
      </div>
      <ul className="divide-y divide-ink/10">
        {interviews.map((item) => (
          <li key={item.id}>
            <a
              href={item.href}
              className="group relative grid items-center gap-x-4 gap-y-1 px-5 py-5 outline-offset-[-3px] transition-colors duration-200 hover:bg-yellow/20 focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none sm:px-6 max-sm:grid-cols-[minmax(0,1fr)_auto] sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_120px_28px]"
            >
              <span aria-hidden="true" className="absolute left-0 top-1/2 h-0 w-[3px] -translate-y-1/2 bg-orange transition-[height] duration-200 group-hover:h-9 motion-reduce:transition-none" />
              <span className="min-w-0 truncate font-serif text-[21px] leading-tight text-ink">{item.role}</span>
              <span className="text-[13.5px] text-ink/60 max-sm:col-start-1 max-sm:row-start-2">{item.completed.replace('Completed ', '')}</span>
              <span className="text-right font-serif text-[22px] text-ink max-sm:col-start-2 max-sm:row-span-2 max-sm:row-start-1 max-sm:self-center">
                {item.score ?? <span className="font-sans text-[13px] text-ink/50">Unavailable</span>}
              </span>
              <ArrowRight size={16} aria-hidden="true" className="text-ink/40 transition-[translate,color] duration-200 group-hover:translate-x-[3px] group-hover:text-ink motion-reduce:transition-none motion-reduce:group-hover:translate-x-0 max-sm:hidden" />
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ResultsTable
