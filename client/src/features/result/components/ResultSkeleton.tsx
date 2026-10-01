const pulse = 'animate-pulse rounded-lg bg-ink/[0.07] motion-reduce:animate-none'

/** Brief layout-preserving placeholder before the "preparing your reflection" message appears. */
function ResultSkeleton() {
  return (
    <div role="status" aria-label="Loading results" className="pt-10 sm:pt-16">
      <div aria-hidden="true" className="flex flex-col gap-5">
        <div className={`h-3 w-32 ${pulse}`} />
        <div className={`h-14 w-72 ${pulse}`} />
        <div className={`h-4 w-56 ${pulse}`} />
        <div className={`mt-12 h-28 w-56 ${pulse}`} />
        {[0, 1, 2, 3].map((i) => <div key={i} className={`h-8 ${pulse}`} />)}
      </div>
    </div>
  )
}

export default ResultSkeleton
