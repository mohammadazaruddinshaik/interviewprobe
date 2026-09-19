function InterviewLoading() {
  return (
    <div className="mx-auto max-w-3xl animate-pulse px-6 pt-20 text-center sm:px-8" aria-busy="true">
      <p className="sr-only" role="status">
        Loading your interview…
      </p>
      <div aria-hidden="true" className="mx-auto h-3 w-28 rounded-full bg-line/70" />
      <div aria-hidden="true" className="mx-auto mt-6 h-7 w-3/4 rounded-full bg-line/70" />
      <div aria-hidden="true" className="mx-auto mt-3 h-7 w-1/2 rounded-full bg-line/70" />
      <div aria-hidden="true" className="mx-auto mt-16 h-48 w-full rounded-2xl bg-line/40" />
    </div>
  )
}

export default InterviewLoading
