const pulse = 'animate-pulse rounded-2xl bg-ink/[0.07] motion-reduce:animate-none'

/** Brief layout-preserving placeholder before the "preparing your evaluation" message appears. */
function ResultSkeleton() {
  return (
    <div role="status" aria-label="Loading results" className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_280px] xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-10">
      <div className="flex flex-col gap-6">
        <div className={`h-28 ${pulse}`} />
        <div className={`h-44 ${pulse}`} />
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <div key={i} className={`h-28 ${pulse}`} />)}
        </div>
      </div>
      <div className={`h-56 max-lg:hidden ${pulse}`} />
    </div>
  )
}

export default ResultSkeleton
