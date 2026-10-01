import { topicLabel } from '@/features/dashboard/lib/labels'
import { questionTypeLabel } from '@/features/interview/lib/progress'
import type { ResultQuestion } from '../types/result'

/** The conversation as it happened, every question treated alike. Nothing is scored or hidden behind a toggle. */
function QuestionReview({ questions }: { questions: ResultQuestion[] }) {
  if (questions.length === 0) return null
  const ordered = [...questions].sort((a, b) => a.sequence - b.sequence)
  return (
    <section data-enter="" aria-labelledby="review-heading" className="rounded-2xl border border-ink/12 bg-white/60 p-6 sm:p-8">
      <h2 id="review-heading" className="font-serif text-[24px] font-normal tracking-[-0.01em] text-ink">
        Conversation review
      </h2>
      <ol className="mt-8 flex flex-col gap-12">
        {ordered.map((q, i) => (
          <li key={q.id} id={`q-${q.id}`} className="grid gap-3 sm:grid-cols-[48px_minmax(0,1fr)] sm:gap-6">
            <span aria-hidden="true" className="font-serif text-[20px] text-ink/60">
              {String(i + 1).padStart(2, '0')}
            </span>
            <div className="min-w-0">
              <h3 id={`q-heading-${q.id}`} tabIndex={-1} className="text-[11px] font-semibold tracking-[0.18em] text-ink/65 outline-offset-4 focus-visible:outline-[3px] focus-visible:outline-yellow">
                QUESTION · {questionTypeLabel(q.type).toUpperCase()} · {topicLabel(q.topic).toUpperCase()}
              </h3>
              <p className="mt-2 font-serif text-[20px] leading-[1.4] text-ink sm:text-[22px]">{q.text}</p>
              <p className="mt-6 text-[11px] font-semibold tracking-[0.18em] text-ink/65">YOUR RESPONSE</p>
              {q.candidate_answer !== null ? (
                <p className="mt-2 whitespace-pre-wrap break-words text-[15.5px] leading-[1.65] text-ink/75">{q.candidate_answer}</p>
              ) : (
                <p className="mt-2 text-[15px] italic text-ink/65">Not answered</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default QuestionReview
