import type { SummaryItem } from '../data/dashboardViewModel'

/** Real backend figures only, each in its own panel. Hidden until something is completed. */
function SummarySection({ items }: { items: SummaryItem[] }) {
  if (items.length === 0) return null
  return (
    <section aria-label="Summary">
      <dl className={`grid gap-4 sm:grid-cols-2 ${items.length > 3 ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
        {items.map((item) => (
          <div key={item.label} data-enter="" className="rounded-2xl border border-ink/12 bg-white/60 p-6">
            <span aria-hidden="true" className="mb-4 block h-[3px] w-7 bg-yellow" />
            <dd className="font-serif text-[38px] leading-none tracking-[-0.015em] text-ink sm:text-[44px]">{item.value}</dd>
            <dt className="mt-3 text-[13.5px] text-ink/65">{item.label}</dt>
            {item.context && <dd className="text-[12.5px] text-ink/50">{item.context}</dd>}
          </div>
        ))}
      </dl>
    </section>
  )
}

export default SummarySection
