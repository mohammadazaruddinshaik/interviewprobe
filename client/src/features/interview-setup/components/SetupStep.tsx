import type { ReactNode } from 'react'

interface SetupStepProps {
  number: string
  title: string
  hint: string
  headingId: string
  children: ReactNode
}

function SetupStep({ number, title, hint, headingId, children }: SetupStepProps) {
  return (
    <section
      data-setup="step"
      aria-labelledby={headingId}
      className="grid gap-3.5 border-t border-ink/[0.08] pt-[22px] first:border-t-0 first:pt-0 xl:grid-cols-[170px_minmax(0,1fr)] xl:gap-5"
    >
      <div className="flex items-baseline gap-3.5 xl:block">
        <span className="w-[26px] shrink-0 font-display text-[13px] font-extrabold tracking-[0.04em] text-forest/55 xl:mb-1.5 xl:block xl:w-auto">
          {number}
        </span>
        <div>
          <h2 id={headingId} className="font-display text-[19px] font-extrabold tracking-[-0.02em] text-deep">
            {title}
          </h2>
          <p className="mt-[3px] text-[13px] text-ink/60">{hint}</p>
        </div>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}

export default SetupStep
