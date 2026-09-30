import { ChevronDown } from 'lucide-react'
import { topicLabel } from '@/features/dashboard/lib/labels'
import { questionTypeLabel } from '@/features/interview/lib/progress'
import type { EvidenceItem, ResultQuestion } from '../types/result'

interface QuestionReviewItemProps {
  question: ResultQuestion
  open: boolean
  onToggle: () => void
  linkedEvidence: EvidenceItem[]
}

function QuestionReviewItem({ question, open, onToggle, linkedEvidence }: QuestionReviewItemProps) {
  const answered = question.candidate_answer !== null
  const buttonId = `q-btn-${question.id}`
  const panelId = `q-panel-${question.id}`
  return (
    <li id={`q-${question.id}`} className="rounded-2xl border border-ink/12 bg-white/60 shadow-[0_1px_2px_rgb(20_42_11/0.04)]">
      <h3>
        <button
          id={buttonId}
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggle}
          className="flex w-full items-center gap-3 rounded-2xl px-4 py-3.5 text-left outline-offset-[-2px] transition-colors duration-200 hover:bg-forest/[0.035] focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none"
        >
          <span className="font-display text-[15px] font-extrabold text-deep">Q{question.sequence}</span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[14px] font-medium text-deep">
              {questionTypeLabel(question.type)} · {topicLabel(question.topic)}
            </span>
          </span>
          <span
            className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11.5px] font-medium ${
              answered ? 'border-forest/30 bg-forest/[0.06] text-forest' : 'border-ink/15 text-ink/55'
            }`}
          >
            {answered ? 'Answered' : 'Unanswered'}
          </span>
          <ChevronDown size={16} aria-hidden="true" className={`shrink-0 text-ink/45 transition-transform duration-200 motion-reduce:transition-none ${open ? 'rotate-180' : ''}`} />
        </button>
      </h3>
      <div id={panelId} role="region" aria-labelledby={buttonId} hidden={!open} className="border-t border-ink/10 px-4 pb-5 pt-4">
        <p className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">QUESTION</p>
        <p className="mt-1.5 font-serif text-[16px] leading-[1.5] text-deep">{question.text}</p>
        <p className="mt-5 text-[11px] font-semibold tracking-[0.18em] text-ink/50">YOUR ANSWER</p>
        {answered ? (
          <p className="mt-1.5 whitespace-pre-wrap break-words text-[14.5px] leading-[1.6] text-ink/80">{question.candidate_answer}</p>
        ) : (
          <p className="mt-1.5 text-[14px] text-ink/55">No answer was submitted.</p>
        )}
        {linkedEvidence.length > 0 && (
          <div className="mt-5">
            <p className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">EVIDENCE</p>
            <ul className="mt-2 flex flex-col gap-2.5">
              {linkedEvidence.map((item, i) => (
                <li key={i} className="rounded-xl border border-yellow/60 bg-yellow/[0.18] px-3.5 py-3">
                  <p className="text-[13.5px] font-semibold text-deep">{item.claim}</p>
                  <p className="mt-1 font-serif text-[14px] leading-snug text-ink/70">{item.evidence}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </li>
  )
}

export default QuestionReviewItem
