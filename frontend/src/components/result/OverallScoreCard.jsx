import GlassCard from '../ui/GlassCard.jsx'
import { ResultsIcon } from '../ui/interviewIcons.jsx'
import ScoreRing from './ScoreRing.jsx'

// Score-band tint — purely a visual read of the real number (never an
// invented evaluative phrase like "Great interview!", which the backend
// has no rule for generating). The heading and supporting line stay
// identical at every band; only the color signal changes.
function bandTone(score) {
  if (score >= 8) return { bg: 'bg-tint-mint-light', border: 'border-success/25', ring: 'var(--color-success)' }
  if (score >= 5) return { bg: 'bg-primary-light-2', border: 'border-primary/25', ring: 'var(--color-primary)' }
  return { bg: 'bg-tint-peach-light', border: 'border-tint-peach/30', ring: 'var(--color-tint-peach)' }
}

// The result banner — a factual completion statement plus the real
// overall score, never an unsupported performance judgment. `metaLine`
// (role · difficulty · question count) is real session metadata shown
// once here for a quick read alongside the score, in addition to the
// fuller breakdown in InterviewSummary.
function OverallScoreCard({ overallScore, metaLine, className = '' }) {
  const tone = bandTone(overallScore)

  return (
    <GlassCard className={`flex flex-col items-center gap-4 border p-5 text-center sm:flex-row sm:justify-between sm:p-6 sm:text-left ${tone.bg} ${tone.border} ${className}`}>
      <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-start">
        <ResultsIcon className="h-6 w-6 shrink-0 text-primary" />
        <div>
          <p className="text-lg font-semibold text-ink">Interview complete</p>
          <p className="mt-1 max-w-sm text-sm leading-relaxed text-muted">
            Your responses have been analyzed across four evaluation dimensions.
          </p>
          {metaLine && <p className="mt-2 text-sm font-medium text-ink/70">{metaLine}</p>}
        </div>
      </div>

      <ScoreRing score={overallScore} label="Overall score" color={tone.ring} size="lg" />
    </GlassCard>
  )
}

export default OverallScoreCard
