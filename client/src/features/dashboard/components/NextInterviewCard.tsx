import { ArrowRight } from 'lucide-react'
import AIInterviewerVisual from './AIInterviewerVisual'
import type { NextInterviewView } from '../data/dashboardViewModel'
import Skeleton from './Skeleton'

function NextInterviewCard({ interview, loading }: { interview: NextInterviewView; loading: boolean }) {
  const show = (text: string) => (loading ? <Skeleton>{text}</Skeleton> : text)
  return (
    <section
      data-dash="next"
      aria-labelledby="next-interview-role"
      aria-busy={loading}
      className="@container rounded-[20px] border border-ink/12 bg-white/60 p-2 shadow-[0_1px_2px_rgb(20_42_11/0.05),0_18px_36px_-24px_rgb(20_42_11/0.3)]"
    >
      <div className="grid gap-2 @[460px]:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="flex flex-col p-5 sm:p-6">
          <p className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/55">
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
            {interview.label}
          </p>
          <h2 id="next-interview-role" className="mt-5 font-display text-[34px] font-extrabold leading-[1.05] tracking-[-0.025em] text-deep sm:text-[40px]">
            {show(interview.role)}
          </h2>
          <p className="mt-1.5 font-serif text-[18px] text-ink/70">{show(interview.subtitle)}</p>

          <ul className="mt-5 flex flex-wrap gap-2">
            {interview.chips.map((item) => (
              <li key={item} className="rounded-full border border-ink/12 bg-cream px-3 py-1 text-[12px] font-medium text-ink/70">
                {show(item)}
              </li>
            ))}
          </ul>

          <a
            href={interview.ctaHref}
            aria-disabled={loading || undefined}
            tabIndex={loading ? -1 : undefined}
            className={`group mt-7 inline-flex h-[50px] w-full items-center justify-center gap-3 self-start rounded-[12px] bg-forest px-7 text-[15px] font-semibold text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(20_42_11/0.3),0_10px_20px_-10px_rgb(20_42_11/0.55)] outline-offset-4 transition-[background-color,box-shadow,translate] duration-200 ease-out hover:-translate-y-0.5 hover:bg-forest-light focus-visible:outline-[3px] focus-visible:outline-yellow active:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0 @[420px]:w-auto ${loading ? 'pointer-events-none opacity-60' : ''}`}
          >
            {interview.cta}
            <ArrowRight size={18} aria-hidden="true" className="transition-transform duration-200 ease-out group-hover:translate-x-1 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0" />
          </a>
        </div>

        <AIInterviewerVisual />
      </div>
    </section>
  )
}

export default NextInterviewCard
