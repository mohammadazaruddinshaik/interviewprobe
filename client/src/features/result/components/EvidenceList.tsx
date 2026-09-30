import { topicLabel } from '@/features/dashboard/lib/labels'
import type { EvidenceItem } from '../types/result'

interface EvidenceListProps {
  evidence: EvidenceItem[]
  /** Question ids present in this result; "View question" only appears for a real match. */
  knownQuestionIds: Set<string>
  onViewQuestion: (questionId: string) => void
}

function EvidenceList({ evidence, knownQuestionIds, onViewQuestion }: EvidenceListProps) {
  if (evidence.length === 0) return null
  return (
    <section data-result="evidence" aria-labelledby="evidence-heading">
      <h2 id="evidence-heading" className="font-display text-[22px] font-extrabold tracking-[-0.02em] text-deep">
        Evidence
      </h2>
      <ul className="mt-4 flex flex-col gap-3">
        {evidence.map((item, i) => {
          const linked = item.question_id && knownQuestionIds.has(item.question_id) ? item.question_id : null
          return (
            <li key={i} className="rounded-2xl border border-ink/12 bg-white/60 p-5 shadow-[0_1px_2px_rgb(20_42_11/0.04)]">
              {item.topic && (
                <p className="text-[11px] font-semibold tracking-[0.18em] text-ink/45">{topicLabel(item.topic).toUpperCase()}</p>
              )}
              <p className="mt-1.5 text-[15px] font-semibold leading-snug text-deep">{item.claim}</p>
              <p className="mt-2 font-serif text-[15px] leading-[1.5] text-ink/70">{item.evidence}</p>
              {linked && (
                <button
                  type="button"
                  onClick={() => onViewQuestion(linked)}
                  className="mt-3 rounded-lg text-[13px] font-semibold text-forest underline-offset-4 outline-offset-2 hover:underline focus-visible:outline-[3px] focus-visible:outline-yellow"
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
