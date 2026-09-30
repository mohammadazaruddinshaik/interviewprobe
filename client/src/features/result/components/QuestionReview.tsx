import type { EvidenceItem, ResultQuestion } from '../types/result'
import QuestionReviewItem from './QuestionReviewItem'

interface QuestionReviewProps {
  questions: ResultQuestion[]
  evidence: EvidenceItem[]
  openIds: Set<string>
  onToggle: (id: string) => void
  onSetAll: (open: boolean) => void
}

function QuestionReview({ questions, evidence, openIds, onToggle, onSetAll }: QuestionReviewProps) {
  if (questions.length === 0) return null
  const allOpen = questions.every((q) => openIds.has(q.id))
  return (
    <section data-result="review" aria-labelledby="review-heading">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="review-heading" className="font-display text-[22px] font-extrabold tracking-[-0.02em] text-deep">
          Question review
        </h2>
        <button
          type="button"
          onClick={() => onSetAll(!allOpen)}
          className="rounded-lg px-1 py-1 text-[13px] font-semibold text-forest outline-offset-2 hover:underline focus-visible:outline-[3px] focus-visible:outline-yellow"
        >
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>
      <ul className="mt-4 flex flex-col gap-2.5">
        {questions.map((q) => (
          <QuestionReviewItem
            key={q.id}
            question={q}
            open={openIds.has(q.id)}
            onToggle={() => onToggle(q.id)}
            linkedEvidence={evidence.filter((e) => e.question_id === q.id)}
          />
        ))}
      </ul>
    </section>
  )
}

export default QuestionReview
