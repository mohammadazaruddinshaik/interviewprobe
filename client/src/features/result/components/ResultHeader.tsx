import { difficultyLabel, roleLabel } from '@/features/dashboard/lib/labels'
import { formatCompletedDate, formatDuration } from '../lib/duration'
import type { InterviewResult } from '../types/result'

function ResultHeader({ result }: { result: InterviewResult }) {
  const { interview, questions } = result
  const answered = questions.filter((q) => q.candidate_answer !== null).length
  const date = formatCompletedDate(interview.completed_at)
  const duration = formatDuration(interview.started_at, interview.completed_at)
  const meta = [
    date && `Completed ${date}`,
    duration,
    `${answered} of ${questions.length} ${questions.length === 1 ? 'question' : 'questions'} answered`,
  ].filter(Boolean) as string[]

  return (
    <header data-result="header">
      <p className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/45">
        <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
        INTERVIEW COMPLETE
      </p>
      <h1 className="mt-3.5 font-display text-[32px] font-extrabold leading-[1.08] tracking-[-0.025em] text-deep sm:text-[40px] xl:text-[46px]">
        Interview complete.
        <span className="block text-deep/45">
          {roleLabel(interview.role)} · {difficultyLabel(interview.difficulty)}
        </span>
      </h1>
      <p className="mt-3.5 font-serif text-[16.5px] leading-[1.5] text-ink/70">{meta.join(' · ')}</p>
    </header>
  )
}

export default ResultHeader
