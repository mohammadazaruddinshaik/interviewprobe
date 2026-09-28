import { ChevronDownIcon } from '../ui/icons.jsx'
import GlassCard from '../ui/GlassCard.jsx'
import { TOPIC_LABELS } from '../../data/interviewCatalog.js'

// The evaluator's cited evidence for its own scores — real quotes/claims
// tied back to a specific question when one is known, never fabricated.
// Kept as a disclosure (collapsed by default) since it's supporting detail
// for someone who wants to see the reasoning, not primary content.
function EvidenceSection({ evidence, questions, className = '' }) {
  if (evidence.length === 0) return null

  const questionById = new Map(questions.map((q) => [q.id, q]))

  return (
    <GlassCard className={`p-5 sm:p-6 ${className}`}>
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 [&::-webkit-details-marker]:hidden">
          <h2 className="text-base font-semibold text-ink">Evidence ({evidence.length})</h2>
          <ChevronDownIcon className="h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-open:rotate-180" />
        </summary>

        <div className="mt-4 flex flex-col divide-y divide-line">
          {evidence.map((item, index) => {
            const question = item.question_id ? questionById.get(item.question_id) : null
            const topic = question?.topic ?? item.topic
            const label = [
              question ? `Question ${question.sequence}` : null,
              topic ? (TOPIC_LABELS[topic] ?? topic) : null,
            ]
              .filter(Boolean)
              .join(' · ')

            return (
              <div key={index} className={index === 0 ? 'pb-4' : 'py-4'}>
                {label && <p className="text-xs font-semibold uppercase tracking-wide text-primary">{label}</p>}
                <p className="mt-1.5 text-sm leading-relaxed text-ink">
                  <span className="font-medium">Claim: </span>
                  {item.claim}
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">
                  <span className="font-medium text-ink/70">Evidence: </span>
                  {item.evidence}
                </p>
              </div>
            )
          })}
        </div>
      </details>
    </GlassCard>
  )
}

export default EvidenceSection
