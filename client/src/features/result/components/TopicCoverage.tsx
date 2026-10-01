import { topicLabel } from '@/features/dashboard/lib/labels'
import { isCovered } from '../lib/coverage'
import type { ResultTopic } from '../types/result'

/** Only topics the conversation actually reached. Pending topics are never listed: that would expose the hidden plan. */
function TopicCoverage({ topics }: { topics: ResultTopic[] }) {
  const reached = topics.filter(isCovered).sort((a, b) => a.sequence_number - b.sequence_number)
  if (reached.length === 0) return null
  return (
    <section data-enter="" aria-labelledby="topics-heading" className="rounded-2xl border border-ink/12 bg-white/60 p-6 sm:p-8">
      <h2 id="topics-heading" className="text-[11px] font-semibold tracking-[0.2em] text-ink/55">
        TOPICS DISCUSSED
      </h2>
      <ul className="mt-4 flex flex-wrap gap-x-3 gap-y-2 text-[15.5px] text-ink/80">
        {reached.map((t, i) => (
          <li key={t.topic} className="flex items-center gap-3">
            {topicLabel(t.topic)}
            {i < reached.length - 1 && <span aria-hidden="true" className="text-ink/30">·</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}

export default TopicCoverage
