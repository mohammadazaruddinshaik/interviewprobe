import ScoreBar from '../result/ScoreBar.jsx'
import GlassCard from '../ui/GlassCard.jsx'
import SectionHeading from '../ui/SectionHeading.jsx'

// Reuses the real result-page ScoreBar component (see
// src/components/result/ScoreBar.jsx) with illustrative example numbers —
// the same four dimensions every real evaluation actually scores
// (backend/app/evaluation), not a fabricated product claim.
const EXAMPLE_SCORES = [
  { label: 'Technical Knowledge', score: 8.5 },
  { label: 'Reasoning', score: 8.0 },
  { label: 'Depth', score: 7.5 },
  { label: 'Communication', score: 8.5 },
]

function EvaluationSection() {
  return (
    <section id="evaluation" className="scroll-mt-28 px-6 py-20">
      <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-2 lg:items-center lg:gap-16">
        <SectionHeading
          eyebrow="Structured Evaluation"
          title="Feedback you can actually act on."
          description="Once the interview ends, every answer is scored across the dimensions that matter — with the reasoning behind each score, not just a number."
        />

        <GlassCard className="p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Example feedback</p>
          <div className="mt-5 flex flex-col gap-5">
            {EXAMPLE_SCORES.map((dimension) => (
              <ScoreBar key={dimension.label} label={dimension.label} score={dimension.score} />
            ))}
          </div>
        </GlassCard>
      </div>
    </section>
  )
}

export default EvaluationSection
