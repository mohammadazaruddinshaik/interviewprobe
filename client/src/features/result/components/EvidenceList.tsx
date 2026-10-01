import { topicLabel } from '@/features/dashboard/lib/labels'
import type { EvidenceItem } from '../types/result'

interface EvidenceListProps {
  evidence: EvidenceItem[]
  /** Question ids present in this result; "View question" only appears for a real match. */
  knownQuestionIds: Set<string>
  onViewQuestion: (questionId: string) => void
}

/** Each claim followed by the supporting text exactly as the backend returned it. */
function EvidenceList({ evidence, knownQuestionIds, onViewQuestion }: EvidenceListProps) {
  if (evidence.length === 0) return null
  return (
    <section data-enter="" aria-labelledby="evidence-heading" className="rounded-2xl border border-ink/12 bg-white/60 p-6 sm:p-8">
      <h2 id="evidence-heading" className="font-serif text-[24px] font-normal tracking-[-0.01em] text-ink">
        Evidence from the conversation
      </h2>
      <ul className="mt-6 flex flex-col divide-y divide-ink/10">
        {evidence.map((item, i) => {
          const linked = item.question_id && knownQuestionIds.has(item.question_id) ? item.question_id : null
          return (
            <li key={i} className="py-6 first:pt-0">
              {item.topic && <p className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">{topicLabel(item.topic).toUpperCase()}</p>}
              <p className="mt-1.5 text-[16px] font-semibold leading-snug text-ink">{item.claim}</p>
              <p className="mt-2.5 border-l-2 border-yellow pl-4 font-serif text-[15.5px] leading-[1.6] text-ink/65">{item.evidence}</p>
              {linked && (
                <button
                  type="button"
                  onClick={() => onViewQuestion(linked)}
                  className="mt-3.5 min-h-9 rounded-lg text-[13.5px] font-semibold text-ink underline decoration-yellow decoration-2 underline-offset-4 outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow"
                >
                  View question
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default EvidenceList
