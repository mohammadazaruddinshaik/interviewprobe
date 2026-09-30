import type { StatView } from '../data/dashboardViewModel'
import Skeleton from './Skeleton'

function StatsRow({ stats, loading }: { stats: StatView[]; loading: boolean }) {
  const show = (text: string) => (loading ? <Skeleton>{text}</Skeleton> : text)
  return (
    <section data-dash="stats" aria-label="Your stats" aria-busy={loading}>
      <dl className="grid grid-cols-1 divide-y divide-ink/10 border-y border-ink/10 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        {stats.map((stat, i) => (
          <div key={stat.label} className={`py-5 sm:py-6 ${i === 0 ? 'sm:pr-6' : 'sm:px-6'}`}>
            <dd className="font-display text-[38px] font-extrabold leading-none tracking-[-0.03em] text-deep">{show(stat.value)}</dd>
            <dt className="mt-2 text-[14px] font-medium text-ink/75">{stat.label}</dt>
            {/* Non-breaking space keeps the row height when there is no truthful context to show. */}
            <dd className="mt-1 text-[12.5px] font-medium text-forest/70">
              {stat.context === null ? ' ' : show(stat.context)}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export default StatsRow
