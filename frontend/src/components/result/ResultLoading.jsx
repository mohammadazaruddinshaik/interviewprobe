import InterviewProbeLoader from '../ui/InterviewProbeLoader.jsx'

// A skeleton shaped like the real layout below it (summary + score card,
// then breakdown, then feedback) rather than generic bars — so the page
// doesn't visually jump once the real result arrives. Never renders a
// placeholder score or placeholder feedback text.
function SkeletonBlock({ className = '' }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-2xl bg-line/60 ${className}`} />
}

function ResultLoading() {
  return (
    <div className="flex flex-col gap-5 px-4 pb-10 pt-6 sm:px-6 lg:px-8" aria-busy="true">
      <p className="sr-only" role="status">
        Loading your results…
      </p>
      <InterviewProbeLoader label="Preparing your evaluation" className="py-4" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SkeletonBlock className="h-32" />
        <SkeletonBlock className="h-32" />
      </div>
      <SkeletonBlock className="h-56" />
      <SkeletonBlock className="h-64" />
      <SkeletonBlock className="h-72" />
    </div>
  )
}

export default ResultLoading
