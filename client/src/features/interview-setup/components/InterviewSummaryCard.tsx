import AdaptivePreview from './AdaptivePreview'
import StartButton from './StartButton'

interface InterviewSummaryCardProps {
  roleLabel: string
  meta: string
  canSubmit: boolean
  busy: boolean
  busyLabel: string
  error: string | null
  loading: boolean
  onStart: () => void
}

function InterviewSummaryCard({ roleLabel, meta, canSubmit, busy, busyLabel, error, loading, onStart }: InterviewSummaryCardProps) {
  return (
    <aside data-enter="" aria-label="Interview summary" className="lg:sticky lg:top-[84px]">
      <div aria-busy={loading} className="rounded-[20px] border border-ink/12 bg-white/60 p-2 shadow-[0_1px_2px_rgb(20_42_11/0.05),0_18px_36px_-24px_rgb(20_42_11/0.3)]">
        <div className="px-5 pb-4 pt-5">
          <p className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/45">
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
            YOUR INTERVIEW
          </p>
          <div aria-live="polite">
            <h2 className={`mt-4 font-display text-[30px] font-extrabold leading-[1.05] tracking-[-0.025em] text-deep ${loading ? 'animate-pulse rounded-md bg-ink/[0.08] text-transparent motion-reduce:animate-none' : ''}`}>
              {roleLabel}
            </h2>
            <p className={`mt-1.5 font-serif text-[17px] text-ink/70 ${loading ? 'animate-pulse rounded-md bg-ink/[0.08] text-transparent motion-reduce:animate-none' : ''}`}>{meta}</p>
            <p className="mt-4 text-[13px] leading-[1.45] text-ink/60">
              Topics, difficulty and length are planned for you when you start.
            </p>
          </div>
        </div>

        <AdaptivePreview />

        <div className="px-3 pb-3.5 pt-4 max-lg:hidden">
          <StartButton disabled={!canSubmit} busy={busy} busyLabel={busyLabel} onClick={onStart} className="h-[54px] w-full text-[16px] font-semibold" />
          <p role={error ? 'alert' : undefined} className={`mt-2.5 min-h-[18px] text-center text-[12.5px] ${error ? 'text-orange' : 'text-ink/60'}`}>
            {error ?? ''}
          </p>
        </div>
      </div>
    </aside>
  )
}

export default InterviewSummaryCard
