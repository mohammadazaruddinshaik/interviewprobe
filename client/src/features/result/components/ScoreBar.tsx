import { barWidth } from '../lib/scoreFormat'

/** Decorative 0-10 hairline in neutral charcoal. The number beside it is the accessible source of truth. */
function ScoreBar({ score }: { score: number }) {
  return (
    <div aria-hidden="true" className="h-[3px] rounded-full bg-ink/10">
      <div className="h-full rounded-full bg-ink/80" style={{ width: barWidth(score) }} />
    </div>
  )
}

export default ScoreBar
