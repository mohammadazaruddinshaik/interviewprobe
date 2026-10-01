function ResultActions() {
  return (
    <div data-enter="" className="flex flex-col gap-3 sm:flex-row">
      <a
        href="/app"
        className="inline-flex h-[54px] items-center justify-center rounded-xl bg-yellow px-8 text-[16px] font-semibold text-ink outline-offset-4 transition-transform duration-200 hover:-translate-y-0.5 focus-visible:outline-[3px] focus-visible:outline-ink motion-reduce:transition-none motion-reduce:hover:translate-y-0"
      >
        Back to dashboard
      </a>
      <a
        href="/app/interviews/new"
        className="inline-flex h-[54px] items-center justify-center rounded-xl border border-ink/25 px-8 text-[16px] font-semibold text-ink outline-offset-4 transition-colors duration-200 hover:bg-ink/[0.05] focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none"
      >
        Start another interview
      </a>
    </div>
  )
}

export default ResultActions
