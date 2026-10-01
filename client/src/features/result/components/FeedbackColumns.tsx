import type { ResultEvaluation } from '../types/result'

function Column({ title, items, id }: { title: string; items: string[]; id: string }) {
  return (
    <section data-enter="" aria-labelledby={id} className="rounded-2xl border border-ink/12 bg-white/60 p-6 sm:p-8">
      <h2 id={id} className="font-serif text-[24px] font-normal tracking-[-0.01em] text-ink">
        {title}
      </h2>
      <ul className="mt-5 flex flex-col gap-4">
        {items.map((item, i) => (
          <li key={i} className="flex gap-3 text-[15.5px] leading-[1.55] text-ink/80">
            <span aria-hidden="true" className="mt-[10px] size-1.5 shrink-0 rounded-full bg-yellow ring-1 ring-ink/20" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

/** The backend's own text, unedited. A column with nothing in it is simply not shown. */
function FeedbackColumns({ evaluation }: { evaluation: ResultEvaluation }) {
  const hasStrengths = evaluation.strengths.length > 0
  const hasWeaknesses = evaluation.weaknesses.length > 0
  if (!hasStrengths && !hasWeaknesses) return null
  return (
    <div
      className={`grid gap-4 ${hasStrengths && hasWeaknesses ? 'md:grid-cols-2' : ''}`}
    >
      {hasStrengths && <Column id="strengths-heading" title="Strengths" items={evaluation.strengths} />}
      {hasWeaknesses && <Column id="weaknesses-heading" title="Weaknesses" items={evaluation.weaknesses} />}
    </div>
  )
}

export default FeedbackColumns
