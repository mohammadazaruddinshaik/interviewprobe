import type { ResultEvaluation } from '../types/result'
import { formatScore, scoreLabel } from '../lib/scoreFormat'
import ScoreBar from './ScoreBar'

// Fixed order, identical treatment: nothing is ranked or called out as best or worst.
const DIMENSIONS: { key: keyof ResultEvaluation; label: string }[] = [
  { key: 'technical_knowledge_score', label: 'Technical knowledge' },
  { key: 'reasoning_score', label: 'Reasoning' },
  { key: 'depth_score', label: 'Depth' },
  { key: 'communication_score', label: 'Communication' },
]

function DimensionScores({ evaluation }: { evaluation: ResultEvaluation }) {
  return (
    <section aria-label="Scores by dimension">
      <ul className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {DIMENSIONS.map(({ key, label }) => {
          const score = evaluation[key] as number
          return (
            <li key={key} data-enter="" className="rounded-2xl border border-ink/12 bg-white/60 p-5">
              <span className="sr-only">{scoreLabel(label, score)}</span>
              <p aria-hidden="true" className="flex flex-col gap-2">
                <span className="text-[13.5px] text-ink/70">{label}</span>
                <span className="font-serif text-[30px] leading-none text-ink">
                  {formatScore(score)}
                  <span className="ml-1.5 font-sans text-[13px] text-ink/45">/ 10</span>
                </span>
              </p>
              <div className="mt-4">
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
