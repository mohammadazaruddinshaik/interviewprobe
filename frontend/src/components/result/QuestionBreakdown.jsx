import { ChevronDownIcon } from '../ui/icons.jsx'
import { QuestionIcon } from '../ui/interviewIcons.jsx'
import GlassCard from '../ui/GlassCard.jsx'
import Badge from '../ui/Badge.jsx'
import { TOPIC_LABELS } from '../../data/interviewCatalog.js'

// A compact, question-by-question list — each row expands to the
// candidate's own answer (or a real "not answered" state, never a
// fabricated one). The reference shows a per-question score in this list,
// but `GET /interviews/{id}/result` has no per-question score field (only
// four session-wide dimension scores), so rows show the real topic chip
// instead of an invented number. The internal question `type`
// (INITIAL/FOLLOW_UP/DEEP_DIVE/…) is orchestration state and is never
// shown here — only the candidate-facing topic.
function QuestionBreakdown({ questions, className = '' }) {
  return (
    <GlassCard className={`flex flex-col gap-4 p-5 sm:p-6 ${className}`}>
      <div className="flex items-center gap-3">
        <QuestionIcon className="h-5 w-5 shrink-0 text-primary" />
        <div>
          <h2 className="text-base font-semibold text-ink">Question Breakdown</h2>
          <p className="text-sm text-muted">Every question this interview actually asked</p>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        {questions.map((question, index) => (
          <details key={question.id} open={index === 0} className="group rounded-2xl border border-line bg-glass/50">
            <summary className="flex cursor-pointer list-none items-start gap-3 px-3.5 py-2.5 [&::-webkit-details-marker]:hidden">
              <span className="mt-px w-5 shrink-0 text-center text-xs font-semibold tabular-nums text-primary">
                {question.sequence}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium leading-snug text-ink">{question.text}</p>
              </div>
              {TOPIC_LABELS[question.topic] && (
                <Badge tone="neutral" className="hidden shrink-0 sm:inline-flex">
                  {TOPIC_LABELS[question.topic]}
                </Badge>
              )}
              <ChevronDownIcon className="mt-1 h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-open:rotate-180" />
            </summary>

            <div className="border-t border-line px-3.5 py-3">
              {TOPIC_LABELS[question.topic] && (
                <Badge tone="neutral" className="mb-3 sm:hidden">
                  {TOPIC_LABELS[question.topic]}
                </Badge>
              )}
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Your answer</p>
              {question.candidate_answer ? (
                <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed text-ink">{question.candidate_answer}</p>
              ) : (
                <p className="mt-1.5 text-sm italic text-muted">No answer submitted.</p>
              )}
            </div>
          </details>
        ))}
      </div>
    </GlassCard>
  )
}

export default QuestionBreakdown
