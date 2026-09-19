import { ChevronDownIcon } from '../ui/icons.jsx'
import { TOPIC_LABELS } from '../../data/interviewCatalog.js'

function QuestionReview({ questions }) {
  return (
    <section className="border-t border-line/70">
      <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Question-by-question review</h2>

        <div className="mt-5 flex flex-col gap-3">
          {questions.map((question, index) => (
            <details
              key={question.id}
              open={index === 0}
              className="group rounded-2xl border border-line/70 bg-white/60 px-5 py-4"
            >
              <summary className="flex cursor-pointer list-none items-start justify-between gap-4 [&::-webkit-details-marker]:hidden">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-accent">
                    Question {question.sequence} · {TOPIC_LABELS[question.topic] ?? question.topic}
                  </p>
                  <p className="mt-1.5 text-[15px] font-medium leading-snug text-ink">{question.text}</p>
                </div>
                <ChevronDownIcon className="mt-1 h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-open:rotate-180" />
              </summary>

              <div className="mt-4 border-t border-line/70 pt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Your answer</p>
                {question.candidate_answer ? (
                  <p className="mt-2 whitespace-pre-wrap text-[15px] leading-relaxed text-ink">
                    {question.candidate_answer}
                  </p>
                ) : (
                  <p className="mt-2 text-sm italic text-muted">No answer submitted.</p>
                )}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}

export default QuestionReview
