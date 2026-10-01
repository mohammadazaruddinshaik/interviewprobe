import { roleLabel } from '@/features/dashboard/lib/labels'
import { formatCompletedDate, formatDuration } from '../lib/duration'
import type { InterviewResult } from '../types/result'

/** Role, completion date and derived duration first; the question/response counts are quiet, factual metadata. */
function ResultHeader({ result }: { result: InterviewResult }) {
  const { interview, questions } = result
  const responses = questions.filter((q) => q.candidate_answer !== null).length
  const date = formatCompletedDate(interview.completed_at)
  const duration = formatDuration(interview.started_at, interview.completed_at)
  const when = [date && `Completed ${date}`, duration].filter(Boolean).join(' · ')
  const counts = `${questions.length} ${questions.length === 1 ? 'question' : 'questions'} discussed · ${responses} ${responses === 1 ? 'response' : 'responses'}`

  return (
    <header data-enter="">
      <span aria-hidden="true" className="mb-5 block h-[2px] w-10 bg-orange" />
      <p className="text-[11px] font-semibold tracking-[0.2em] text-ink/55">INTERVIEW COMPLETE</p>
      <h1 className="mt-3 font-serif text-[38px] font-normal leading-[1.08] tracking-[-0.015em] text-ink sm:text-[52px]">{roleLabel(interview.role)}</h1>
      {when && <p className="mt-4 text-[15.5px] text-ink/70">{when}</p>}
      <p className="mt-1 text-[13.5px] text-ink/55">{counts}</p>
    </header>
  )
}

export default ResultHeader
