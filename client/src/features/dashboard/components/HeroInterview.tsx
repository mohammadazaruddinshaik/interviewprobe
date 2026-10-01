import { ArrowRight } from 'lucide-react'
import type { PrimaryView } from '../data/dashboardViewModel'
import PresenceArt from './PresenceArt'

/** The centrepiece: what to do next. Shows only the role and lifecycle status of a real interview. */
function HeroInterview({ primary }: { primary: PrimaryView }) {
  return (
    <section
      data-enter=""
      aria-labelledby="hero-heading"
      className="relative overflow-hidden rounded-[28px] border border-ink/12 bg-white/60 shadow-[0_1px_2px_rgb(6_11_7/0.04),0_30px_60px_-40px_rgb(6_11_7/0.35)]"
    >
      <span aria-hidden="true" className="absolute left-0 top-9 h-14 w-[4px] bg-orange" />
      <div className="grid items-center gap-2 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="px-7 pb-2 pt-9 sm:px-10 sm:pt-11 lg:py-12">
          <p id="hero-heading" className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.2em] text-ink/55">
            <span aria-hidden="true" className="size-2 rounded-[2px] bg-yellow" />
            {primary.kind === 'new' ? 'NEXT INTERVIEW' : primary.heading.toUpperCase()}
          </p>
          {primary.role ? (
            <>
              <p className="mt-5 font-serif text-[40px] leading-[1.06] tracking-[-0.015em] text-ink sm:text-[52px]">{primary.role}</p>
              <p className="mt-3 inline-flex items-center gap-2 text-[14px] text-ink/65">
                <span aria-hidden="true" className="size-1.5 rounded-full bg-orange" />
                {primary.note}
              </p>
            </>
          ) : (
            <>
              <p className="mt-5 font-serif text-[36px] leading-[1.08] tracking-[-0.015em] text-ink sm:text-[46px]">Start an interview</p>
              <p className="mt-3 max-w-[420px] text-[15.5px] leading-[1.55] text-ink/65">{primary.note}</p>
            </>
          )}
          <a
            href={primary.ctaHref}
            className="group mt-8 inline-flex h-[54px] w-full items-center justify-center gap-3 rounded-xl bg-yellow px-8 text-[16px] font-semibold text-ink shadow-[0_10px_24px_-14px_rgb(204_70_26/0.7)] outline-offset-4 transition-[translate,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_28px_-14px_rgb(204_70_26/0.75)] focus-visible:outline-[3px] focus-visible:outline-ink motion-reduce:transition-none motion-reduce:hover:translate-y-0 sm:w-auto"
          >
            {primary.cta}
            <ArrowRight size={18} aria-hidden="true" className="transition-transform duration-200 group-hover:translate-x-1 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0" />
          </a>
        </div>
        <PresenceArt className="mx-auto -mb-2 h-auto w-full max-w-[330px] px-4 max-lg:order-first max-lg:mt-8 max-lg:max-w-[240px] lg:max-w-none lg:px-6" />
      </div>
    </section>
  )
}

export default HeroInterview
