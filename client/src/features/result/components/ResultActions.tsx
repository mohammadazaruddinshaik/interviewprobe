function ResultActions() {
  return (
    <div className="flex flex-col gap-2.5">
      <a
        href="/app"
        className="inline-flex h-[50px] items-center justify-center rounded-xl bg-forest px-6 text-[15px] font-semibold text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(20_42_11/0.3),0_10px_20px_-10px_rgb(20_42_11/0.55)] outline-offset-4 transition-[background-color,translate] duration-200 hover:-translate-y-0.5 hover:bg-forest-light focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none motion-reduce:hover:translate-y-0"
      >
        Back to Dashboard
      </a>
      <a
        href="/app/interviews/new"
        className="inline-flex h-[46px] items-center justify-center rounded-xl border border-forest/30 bg-cream px-6 text-[14.5px] font-semibold text-forest outline-offset-4 transition-colors duration-200 hover:bg-forest/[0.05] focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none"
      >
        New Interview
      </a>
    </div>
  )
}

export default ResultActions
