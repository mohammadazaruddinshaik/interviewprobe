import { topicLabel } from '@/features/dashboard/lib/labels'
import { questionTypeLabel } from '../lib/progress'
import type { Question } from '../types/interview'

function QuestionPanel({ question }: { question: Question }) {
  return (
    <section
      data-room="question"
      aria-labelledby="room-question"
      className="rounded-[20px] border border-ink/12 bg-white/60 p-5 shadow-[0_1px_2px_rgb(20_42_11/0.05),0_18px_36px_-24px_rgb(20_42_11/0.3)] sm:p-7"
    >
      <p className="flex flex-wrap items-center gap-2 text-[11px] font-semibold tracking-[0.18em] text-ink/45">
        <span>{topicLabel(question.topic).toUpperCase()}</span>
        <span aria-hidden="true">·</span>
        <span>{questionTypeLabel(question.type).toUpperCase()}</span>
      </p>
      <div aria-live="polite" key={question.id} data-room="question-text">
        {question.lead_in && <p className="mt-4 font-serif text-[16px] italic leading-[1.45] text-ink/60">{question.lead_in}</p>}
        <h1
          id="room-question"
          className="mt-3 text-balance font-display text-[24px] font-extrabold leading-[1.18] tracking-[-0.02em] text-deep sm:text-[30px]"
        >
          {question.text}
        </h1>
      </div>
    </section>
  )
}

export default QuestionPanel
