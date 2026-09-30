import type { ResultEvaluation } from '../types/result'
import { formatScore, scoreLabel } from '../lib/scoreFormat'
import ScoreBar from './ScoreBar'

const DIMENSIONS: { key: keyof ResultEvaluation; label: string }[] = [
  { key: 'technical_knowledge_score', label: 'Technical Knowledge' },
  { key: 'reasoning_score', label: 'Reasoning' },
  { key: 'depth_score', label: 'Depth' },
  { key: 'communication_score', label: 'Communication' },
]

function DimensionScores({ evaluation }: { evaluation: ResultEvaluation }) {
  return (
    <section data-result="dimensions" aria-labelledby="dimensions-heading">
      <h2 id="dimensions-heading" className="font-display text-[22px] font-extrabold tracking-[-0.02em] text-deep">
        Dimension scores
      </h2>
      <ul className="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {DIMENSIONS.map(({ key, label }) => {
          const score = evaluation[key] as number
          return (
            <li key={key} className="rounded-2xl border border-ink/12 bg-white/60 p-4 shadow-[0_1px_2px_rgb(20_42_11/0.04)]">
              <span className="sr-only">{scoreLabel(label, score)}</span>
              <p aria-hidden="true" className="text-[12.5px] font-medium leading-snug text-ink/65">
                {label}
              </p>
              <p aria-hidden="true" className="mt-2 flex items-baseline gap-1.5 text-deep">
                <span className="font-display text-[28px] font-extrabold leading-none tracking-[-0.03em]">{formatScore(score)}</span>
                <span className="text-[13px] font-semibold text-deep/45">/ 10</span>
              </p>
              <div className="mt-3">
                <ScoreBar score={score} />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default DimensionScores
