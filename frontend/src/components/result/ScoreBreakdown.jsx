import GlassCard from '../ui/GlassCard.jsx'
import { AnalyticsIcon } from '../ui/interviewIcons.jsx'
import ScoreRing from './ScoreRing.jsx'

// The four dimensions exactly as the evaluation schema defines them
// (technical_knowledge_score / reasoning_score / depth_score /
// communication_score) — never renamed to the reference's own labels,
// since these are the real, existing candidate-facing names this page has
// always used. Each gets a fixed, identity color (not score-dependent) so
// the same dimension always reads the same color across a session.
function ScoreBreakdown({ evaluation, className = '' }) {
  const dimensions = [
    { label: 'Technical Knowledge', score: evaluation.technical_knowledge_score, color: 'var(--color-primary)' },
    { label: 'Reasoning', score: evaluation.reasoning_score, color: 'var(--color-success)' },
    { label: 'Depth', score: evaluation.depth_score, color: 'var(--color-tint-purple)' },
    { label: 'Communication', score: evaluation.communication_score, color: 'var(--color-tint-peach)' },
  ]

  return (
    <GlassCard className={`flex flex-col gap-5 p-5 sm:p-6 ${className}`}>
      <div className="flex items-center gap-3">
        <AnalyticsIcon className="h-5 w-5 shrink-0 text-primary" />
        <div>
          <h2 className="text-base font-semibold text-ink">Score Breakdown</h2>
          <p className="text-sm text-muted">Performance across key evaluation areas</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {dimensions.map((dimension) => (
          <ScoreRing key={dimension.label} {...dimension} />
        ))}
      </div>
    </GlassCard>
  )
}

export default ScoreBreakdown
