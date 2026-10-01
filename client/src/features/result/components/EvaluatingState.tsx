const pulse = 'animate-pulse rounded-lg bg-ink/[0.07] motion-reduce:animate-none'

/** Shown while GET /result blocks on evaluation generation (or retries EVALUATION_BUSY). No progress is claimed. */
function EvaluatingState() {
  return (
    <section aria-labelledby="evaluating-heading" className="pt-10 sm:pt-16">
      <p className="text-[11px] font-semibold tracking-[0.2em] text-ink/55">INTERVIEW COMPLETE</p>
      <div role="status">
        <h1 id="evaluating-heading" className="mt-4 font-serif text-[34px] font-normal leading-[1.12] tracking-[-0.01em] text-ink sm:text-[46px]">
          Your interview is complete.
          <span className="block text-ink/55">We’re preparing your reflection.</span>
        </h1>
        <p className="mt-4 text-[16px] leading-[1.55] text-ink/65">This can take a little while. You can stay on this page.</p>
      </div>
      <div aria-hidden="true" className="mt-12 flex flex-col gap-5">
        <div className={`h-24 w-48 ${pulse}`} />
        <div className={`h-3 ${pulse}`} />
        <div className={`h-3 w-[85%] ${pulse}`} />
        <div className={`h-3 w-[70%] ${pulse}`} />
      </div>
    </section>
  )
}

export default EvaluatingState
