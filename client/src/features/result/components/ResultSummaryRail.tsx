import { difficultyLabel, roleLabel } from '@/features/dashboard/lib/labels'
import { formatCompletedDate, formatDuration } from '../lib/duration'
import type { InterviewResult } from '../types/result'
import ResultActions from './ResultActions'
import { isCovered } from '../lib/coverage'

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5">
      <dt className="text-[12.5px] text-ink/55">{label}</dt>
      <dd className="text-right text-[14px] font-semibold text-deep">{value}</dd>
    </div>
  )
}

/** Facts are desktop-only (the header already carries them on small screens); the actions always render, last. */
function ResultSummaryRail({ result }: { result: InterviewResult }) {
  const { interview, questions, topics } = result
  const answered = questions.filter((q) => q.candidate_answer !== null).length
  const covered = topics.filter(isCovered).length
  const date = formatCompletedDate(interview.completed_at)
  const duration = formatDuration(interview.started_at, interview.completed_at)
  return (
    <aside data-result="rail" aria-label="Interview summary" className="flex flex-col gap-4 lg:sticky lg:top-[84px]">
      <section aria-labelledby="summary-heading" className="rounded-2xl border border-ink/12 bg-white/60 p-5 shadow-[0_1px_2px_rgb(20_42_11/0.04)] max-lg:hidden">
        <h2 id="summary-heading" className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">
          SUMMARY
        </h2>
        <dl className="mt-2 divide-y divide-ink/10">
          <Fact label="Role" value={roleLabel(interview.role)} />
          <Fact label="Difficulty" value={difficultyLabel(interview.difficulty)} />
          {date && <Fact label="Completed" value={date} />}
          {duration && <Fact label="Duration" value={duration} />}
          <Fact label="Answered" value={`${answered} of ${questions.length}`} />
          {topics.length > 0 && <Fact label="Topics covered" value={`${covered} of ${topics.length}`} />}
        </dl>
      </section>
      <ResultActions />
    </aside>
  )
}

export default ResultSummaryRail
