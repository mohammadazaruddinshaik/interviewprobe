import { formatScore, scoreLabel } from '../lib/scoreFormat'
import ScoreBar from './ScoreBar'

function OverallScoreCard({ score }: { score: number }) {
  return (
    <section
      data-result="overall"
      aria-label="Overall score"
      className="rounded-[20px] border border-ink/12 bg-white/60 p-6 shadow-[0_1px_2px_rgb(20_42_11/0.05),0_18px_36px_-24px_rgb(20_42_11/0.3)] sm:p-8"
    >
      <p className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">OVERALL SCORE</p>
      <p className="mt-3 flex items-baseline gap-3 text-deep">
        <span className="sr-only">{scoreLabel('Overall score', score)}</span>
        <span aria-hidden="true" className="font-display text-[64px] font-extrabold leading-none tracking-[-0.04em] sm:text-[80px]">
          {formatScore(score)}
        </span>
        <span aria-hidden="true" className="font-display text-[22px] font-extrabold text-deep/45 sm:text-[28px]">
          / 10
        </span>
      </p>
      <div className="mt-6">
        <ScoreBar score={score} tall />
      </div>
    </section>
  )
}

export default OverallScoreCard
