function ResultLoading() {
  return (
    <div className="mx-auto max-w-3xl animate-pulse px-6 pt-20 text-center sm:px-8" aria-busy="true">
      <p className="sr-only" role="status">
        Loading your results…
      </p>
      <div aria-hidden="true" className="mx-auto h-7 w-2/3 rounded-full bg-line/70" />
      <div aria-hidden="true" className="mx-auto mt-3 h-7 w-1/2 rounded-full bg-line/70" />
      <div aria-hidden="true" className="mx-auto mt-8 h-16 w-40 rounded-full bg-line/70" />
      <div aria-hidden="true" className="mx-auto mt-6 h-4 w-56 rounded-full bg-line/50" />
      <div className="mt-16 flex flex-col gap-6 text-left">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} aria-hidden="true" className="h-6 w-full rounded-full bg-line/40" />
        ))}
      </div>
    </div>
  )
}

export default ResultLoading
