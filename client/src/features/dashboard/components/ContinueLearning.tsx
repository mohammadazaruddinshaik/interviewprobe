import { ArrowUpRight } from 'lucide-react'
import type { LearningItem } from '../data/dashboardViewModel'
import { railCard } from './PracticeStreak'

function ContinueLearning({ items }: { items: LearningItem[] }) {
  return (
    <section data-dash="rail" aria-labelledby="learning-heading" className={railCard}>
      <h2 id="learning-heading" className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">
        CONTINUE LEARNING
      </h2>
      <ul className="mt-3 divide-y divide-ink/10">
        {items.map((item) => (
          <li key={item.title}>
            <a
              href="#learning"
              className="group -mx-2 flex items-center justify-between gap-3 rounded-lg px-2 py-3 outline-offset-[-2px] transition-colors duration-200 hover:bg-forest/[0.035] focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none"
            >
              <span className="min-w-0">
                <span className="block text-[14px] font-semibold leading-snug text-deep">{item.title}</span>
                <span className="mt-0.5 block text-[12.5px] text-ink/55">{item.detail}</span>
              </span>
              <ArrowUpRight size={16} aria-hidden="true" className="shrink-0 text-ink/35 transition-[translate,color] duration-200 group-hover:-translate-y-px group-hover:translate-x-px group-hover:text-forest motion-reduce:transition-none" />
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default ContinueLearning
