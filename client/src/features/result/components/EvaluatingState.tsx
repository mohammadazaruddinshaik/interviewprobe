const pulse = 'animate-pulse rounded-2xl bg-ink/[0.07] motion-reduce:animate-none'

/** Shown while GET /result blocks on evaluation generation (or retries EVALUATION_BUSY). */
function EvaluatingState() {
  return (
    <section aria-labelledby="evaluating-heading" className="mx-auto max-w-[760px]">
      <p className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/45">
        <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
        INTERVIEW COMPLETE
      </p>
      <div role="status">
        <h1 id="evaluating-heading" className="mt-3.5 font-display text-[30px] font-extrabold leading-[1.1] tracking-[-0.025em] text-deep sm:text-[38px]">
          Your interview is complete.
          <span className="block text-deep/45">We’re preparing your evaluation.</span>
        </h1>
        <p className="mt-3.5 font-serif text-[16.5px] leading-[1.5] text-ink/70">This can take a little while. You can stay on this page.</p>
      </div>
      <div aria-hidden="true" className="mt-8 grid gap-3 sm:grid-cols-2">
        <div className={`h-36 sm:col-span-2 ${pulse}`} />
        <div className={`h-24 ${pulse}`} />
        <div className={`h-24 ${pulse}`} />
      </div>
    </section>
  )
}

export default EvaluatingState
