import { barWidth } from '../lib/scoreFormat'

/** Decorative 0-10 bar. The number beside it is the accessible source of truth. */
function ScoreBar({ score, tall = false }: { score: number; tall?: boolean }) {
  return (
    <div aria-hidden="true" className={`overflow-hidden rounded-full bg-forest/10 ${tall ? 'h-2' : 'h-1.5'}`}>
      <div className="h-full rounded-full bg-forest" style={{ width: barWidth(score) }} />
    </div>
  )
}

export default ScoreBar
