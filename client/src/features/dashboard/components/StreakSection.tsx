import type { StreakView } from '../data/dashboardViewModel'

/** The backend's real streak and last seven days of activity, as a calm rhythm rather than a game. */
function StreakSection({ streak }: { streak: StreakView }) {
  return (
    <section data-enter="" aria-labelledby="streak-heading" className="rounded-2xl border border-ink/12 bg-white/60 p-6 sm:p-7">
      <h2 id="streak-heading" className="text-[11px] font-semibold tracking-[0.2em] text-ink/55">
        INTERVIEW STREAK
      </h2>
      <p className="mt-3 font-serif text-[30px] leading-none tracking-[-0.01em] text-ink">{streak.title}</p>
      <ol aria-label="Last seven days" className="mt-6 grid grid-cols-7 gap-1.5">
        {streak.week.map((day) => (
          <li key={day.title} className="flex flex-col items-center gap-2" title={day.title}>
            <span className="sr-only">{day.title}</span>
            <span
              aria-hidden="true"
              className={`size-[26px] rounded-full border ${day.active ? 'border-ink bg-yellow' : 'border-ink/20 bg-transparent'} ${day.today ? 'ring-2 ring-ink/25 ring-offset-2 ring-offset-cream' : ''}`}
            />
            <span aria-hidden="true" className={`text-[10.5px] font-medium ${day.today ? 'text-ink' : 'text-ink/50'}`}>
              {day.label}
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default StreakSection
