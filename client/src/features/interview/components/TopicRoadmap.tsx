import { Check } from 'lucide-react'
import { topicLabel } from '@/features/dashboard/lib/labels'
import type { TopicEntry, TranscriptEntry } from '../types/interview'

const railCard = 'rounded-2xl border border-ink/12 bg-white/60 p-5 shadow-[0_1px_2px_rgb(20_42_11/0.04)]'

function TopicRoadmap({ topics, transcript }: { topics: TopicEntry[]; transcript: TranscriptEntry[] }) {
  const ordered = [...topics].sort((a, b) => a.sequence_number - b.sequence_number)
  return (
    <aside data-room="rail" aria-label="Interview context" className="flex min-w-0 flex-col gap-4">
      <section aria-labelledby="roadmap-heading" className={railCard}>
        <h2 id="roadmap-heading" className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">
          TOPICS
        </h2>
        <ul className="mt-4 flex flex-col gap-3">
          {ordered.map((t) => (
            <li key={t.topic} className="flex items-center gap-3 text-[14px]">
              <span
                aria-hidden="true"
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-[1.5px] ${
                  t.status === 'COMPLETED' ? 'border-forest bg-forest text-cream' : t.status === 'IN_PROGRESS' ? 'border-yellow bg-yellow/40' : 'border-ink/25'
                }`}
              >
                {t.status === 'COMPLETED' && <Check size={12} strokeWidth={3} />}
              </span>
              <span className={t.status === 'IN_PROGRESS' ? 'font-semibold text-deep' : t.status === 'COMPLETED' ? 'text-ink/60' : 'text-ink/70'}>
                {topicLabel(t.topic)}
              </span>
              <span className="sr-only">
                {t.status === 'COMPLETED' ? 'covered' : t.status === 'IN_PROGRESS' ? 'current topic' : 'not started'}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {transcript.length > 0 && (
        <section aria-labelledby="transcript-heading" className={railCard}>
          <h2 id="transcript-heading" className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">
            THIS SESSION
          </h2>
          <ol className="mt-3 divide-y divide-ink/10">
            {transcript.map((entry) => (
              <li key={entry.questionId} className="py-3 first:pt-0 last:pb-0">
                <p className="line-clamp-2 text-[13px] font-semibold leading-snug text-deep">Q{entry.sequence}. {entry.question}</p>
                <p className="mt-1 line-clamp-2 text-[12.5px] leading-snug text-ink/60">{entry.answer}</p>
              </li>
            ))}
          </ol>
          <p className="mt-3 text-[11.5px] text-ink/45">Only kept while this page stays open.</p>
        </section>
      )}
    </aside>
  )
}

export default TopicRoadmap
