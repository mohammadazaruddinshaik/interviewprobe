import type { ResultEvaluation } from '../types/result'

function FeedbackCard({ title, items, empty, id }: { title: string; items: string[]; empty: string; id: string }) {
  return (
    <section aria-labelledby={id} className="rounded-2xl border border-ink/12 bg-white/60 p-5 shadow-[0_1px_2px_rgb(20_42_11/0.04)] sm:p-6">
      <h2 id={id} className="font-display text-[20px] font-extrabold tracking-[-0.02em] text-deep">
        {title}
      </h2>
      {items.length === 0 ? (
        <p className="mt-3 text-[14px] text-ink/55">{empty}</p>
      ) : (
        <ul className="mt-4 flex flex-col gap-3.5">
          {items.map((item, i) => (
            <li key={i} className="flex gap-3 text-[14.5px] leading-[1.5] text-deep">
              <span aria-hidden="true" className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-yellow ring-1 ring-forest/30" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function FeedbackColumns({ evaluation }: { evaluation: ResultEvaluation }) {
  return (
    <div data-result="feedback" className="grid gap-4 md:grid-cols-2">
      <FeedbackCard id="strengths-heading" title="Strengths" items={evaluation.strengths} empty="No strengths were recorded." />
      <FeedbackCard id="improvements-heading" title="Improvements" items={evaluation.weaknesses} empty="No improvement areas were recorded." />
    </div>
  )
}

export default FeedbackColumns
