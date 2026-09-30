import type { PracticedTopicsView } from '../data/dashboardViewModel'
import { railCard } from './PracticeStreak'
import Skeleton from './Skeleton'

// The backend reports only HOW MANY topics were practiced, not per-topic progress,
// so this card shows that truthful summary plus the topics from recent interviews.
function PracticedTopics({ topics, loading }: { topics: PracticedTopicsView; loading: boolean }) {
  return (
    <section data-dash="rail" aria-labelledby="topics-heading" aria-busy={loading} className={railCard}>
      <h2 id="topics-heading" className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">
        TOPICS PRACTICED
      </h2>
      <p className="mt-3 text-[14px] leading-snug text-deep">
        {loading ? <Skeleton>{topics.summary}</Skeleton> : topics.summary}
      </p>

      {!loading && topics.recentTopics.length > 0 && (
        <>
          <p className="mt-4 text-[12px] font-medium text-ink/50">In your recent interviews</p>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {topics.recentTopics.map((topic) => (
              <li key={topic} className="rounded-full border border-ink/12 bg-cream px-2.5 py-1 text-[12px] font-medium text-ink/70">
                {topic}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

export default PracticedTopics
