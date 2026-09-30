import { Flame } from 'lucide-react'
import type { StreakView } from '../data/dashboardViewModel'
import Skeleton from './Skeleton'

const railCard =
  'rounded-2xl border border-ink/12 bg-white/60 p-5 shadow-[0_1px_2px_rgb(20_42_11/0.04)] transition-[translate,box-shadow] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_14px_28px_-20px_rgb(20_42_11/0.35)] motion-reduce:transition-none motion-reduce:hover:translate-y-0'

const STATE_LABEL = { done: 'practiced', today: 'today', missed: 'no practice', upcoming: 'upcoming' } as const

function PracticeStreak({ streak, loading }: { streak: StreakView; loading: boolean }) {
  return (
    <section data-dash="rail" aria-labelledby="streak-heading" aria-busy={loading} className={railCard}>
      <h2 id="streak-heading" className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">
        PRACTICE STREAK
      </h2>
      <p className="mt-3 flex items-center gap-2 font-display text-[30px] font-extrabold leading-none tracking-[-0.02em] text-deep">
        <Flame size={22} aria-hidden="true" className="text-orange" />
        {loading ? <Skeleton>{streak.title}</Skeleton> : streak.title}
      </p>
      <p className="mt-1.5 text-[13px] text-ink/60">{loading ? <Skeleton>{streak.message}</Skeleton> : streak.message}</p>

      <ol className="mt-5 grid grid-cols-7 gap-1.5">
        {streak.week.map((day) => (
          <li key={day.label} className="flex flex-col items-center gap-1.5">
            <span
              aria-label={`${day.label}: ${STATE_LABEL[day.state]}`}
              className={`h-7 w-7 rounded-full border ${
                day.state === 'done'
                  ? 'border-forest bg-forest'
                  : day.state === 'today'
                    ? 'border-yellow bg-yellow/40 ring-2 ring-yellow/60'
                    : 'border-ink/15 bg-transparent'
              }`}
            />
            <span className="text-[10.5px] font-medium text-ink/50">{day.label}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default PracticeStreak
export { railCard }
