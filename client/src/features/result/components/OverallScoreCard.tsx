import { formatScore, scoreLabel } from '../lib/scoreFormat'

/** The score stands alone: no verdict, label or comparison. */
function OverallScoreCard({ score }: { score: number }) {
  return (
    <section data-enter="" aria-labelledby="reflection-heading" className="rounded-2xl border border-ink/12 bg-white/60 p-6 sm:p-8">
      <h2 id="reflection-heading" className="text-[11px] font-semibold tracking-[0.2em] text-ink/55">
        YOUR INTERVIEW REFLECTION
      </h2>
      <p className="mt-5 flex items-baseline gap-3">
        <span className="sr-only">{scoreLabel('Overall score', score)}</span>
        <span aria-hidden="true" className="bg-gradient-to-t from-yellow from-[26%] to-transparent to-[26%] px-1 font-serif text-[88px] font-normal leading-none tracking-[-0.03em] text-ink sm:text-[120px]">
          {formatScore(score)}
        </span>
        <span aria-hidden="true" className="font-serif text-[26px] text-ink/50 sm:text-[34px]">
          / 10
        </span>
      </p>
    </section>
  )
}

export default OverallScoreCard
