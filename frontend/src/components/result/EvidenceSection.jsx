import { ChevronDownIcon } from '../ui/icons.jsx'
import { TOPIC_LABELS } from '../../data/interviewCatalog.js'

function EvidenceSection({ evidence, questions }) {
  if (evidence.length === 0) return null

  const questionById = new Map(questions.map((q) => [q.id, q]))

  return (
    <section className="border-t border-line/70">
      <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8">
        <details className="group">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 [&::-webkit-details-marker]:hidden">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Evidence ({evidence.length})
            </h2>
            <ChevronDownIcon className="h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-open:rotate-180" />
          </summary>

          <div className="mt-5 flex flex-col divide-y divide-line/70">
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
                <div key={index} className={index === 0 ? 'pb-5' : 'py-5'}>
                  {label && (
                    <p className="text-xs font-semibold uppercase tracking-wide text-accent">{label}</p>
                  )}
                  <p className="mt-2 text-[15px] leading-relaxed text-ink">
                    <span className="font-medium">Claim: </span>
                    {item.claim}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-muted">
                    <span className="font-medium text-ink/70">Evidence: </span>
                    {item.evidence}
                  </p>
                </div>
              )
            })}
          </div>
        </details>
      </div>
    </section>
  )
}

export default EvidenceSection
