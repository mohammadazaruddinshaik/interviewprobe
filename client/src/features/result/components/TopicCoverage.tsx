import { Check } from 'lucide-react'
import { topicLabel } from '@/features/dashboard/lib/labels'
import { isCovered } from '../lib/coverage'
import type { ResultTopic } from '../types/result'

function TopicCoverage({ topics }: { topics: ResultTopic[] }) {
  if (topics.length === 0) return null
  const ordered = [...topics].sort((a, b) => a.sequence_number - b.sequence_number)
  return (
    <section data-result="topics" aria-labelledby="coverage-heading">
      <h2 id="coverage-heading" className="font-display text-[22px] font-extrabold tracking-[-0.02em] text-deep">
        Topic coverage
      </h2>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2">
        {ordered.map((t) => {
          const covered = isCovered(t)
          return (
            <li key={t.topic} className="flex items-center justify-between gap-3 rounded-xl border border-ink/12 bg-white/60 px-4 py-3">
              <span className="flex items-center gap-3 text-[14.5px] font-medium text-deep">
                <span
                  aria-hidden="true"
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-[1.5px] ${covered ? 'border-forest bg-forest text-cream' : 'border-ink/25'}`}
                >
                  {covered && <Check size={12} strokeWidth={3} />}
                </span>
                {topicLabel(t.topic)}
              </span>
              <span className={`text-[12.5px] font-medium ${covered ? 'text-forest' : 'text-ink/50'}`}>{covered ? 'Covered' : 'Not reached'}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default TopicCoverage
